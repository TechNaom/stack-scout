"""Shared core for every stack-scout script: clock, token, redaction, facts file, run meter.

State lives in state_dir(): run.json (the run meter) and facts-<run day>.json.
Files that exist but are not valid JSON, or do not pass their schema, raise
CoreError (a ValueError); a script catches it, prints {"ok": false, "error": ...}
and exits EXIT_BLOCKED. Nothing here prints or stores the GitHub token.
"""
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

import schema

ROOT = pathlib.Path(__file__).resolve().parent.parent

EXIT_OK = 0
EXIT_BLOCKED = 2
EXIT_RATE_LIMITED = 3

_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class CoreError(ValueError):
    """Bad state or settings: a script reports it as JSON and exits EXIT_BLOCKED."""


def now_utc() -> str:
    """UTC now as 2026-11-27T10:00:00Z, or $STACK_SCOUT_NOW when set and non-empty."""
    fixed = os.environ.get("STACK_SCOUT_NOW", "")
    if not fixed:
        return datetime.datetime.now(datetime.timezone.utc).strftime(_FORMAT)
    try:
        if not _STAMP.fullmatch(fixed):
            raise ValueError
        datetime.datetime.strptime(fixed, _FORMAT)
    except ValueError:
        raise CoreError(f"STACK_SCOUT_NOW must look like 2026-11-27T10:00:00Z, got {fixed!r}") from None
    return fixed


def today_utc() -> str:
    return now_utc()[:10]


def state_dir() -> pathlib.Path:
    """$STACK_SCOUT_DIR if set and non-empty, else ./.stack-scout; created if missing."""
    path = pathlib.Path(os.environ.get("STACK_SCOUT_DIR") or ".stack-scout")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_token():
    """$GITHUB_TOKEN if non-blank, else `gh auth token`; None on any failure. Never logged."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    if os.environ.get("STACK_SCOUT_NO_GH") == "1":
        return None
    try:
        proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=5)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    out = (proc.stdout or "").strip()
    return out if proc.returncode == 0 and out else None


def redact(text: str, token) -> str:
    """Replace every occurrence of token with ***; None or "" leaves text unchanged."""
    return text.replace(token, "***") if token else text


def _read_json(path, name):
    """Parse path and check it against schema `name`; None when the file is missing."""
    path = pathlib.Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise CoreError(f"cannot read {path.name}: {exc}") from None
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise CoreError(f"{path.name} is not valid JSON: {exc}") from None
    errors = schema.validate(data, schema.load(name))
    if errors:
        raise CoreError(f"{path.name} does not match the {name} schema: {'; '.join(errors[:3])}")
    return data


def _write_json(path, data, name):
    """Check data against schema `name`, then write it atomically (UTF-8, LF, 2-space indent)."""
    errors = schema.validate(data, schema.load(name))
    if errors:
        raise CoreError(f"refusing to write invalid {name} data: {'; '.join(errors[:3])}")
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _run_path():
    return state_dir() / "run.json"


def new_run() -> dict:
    """A fresh run.json body, started now."""
    return {"schema": 1, "started": now_utc(), "ended": None, "script_calls": 0,
            "github_points": 0, "questions_asked": 0, "partial": False}


def load_run():
    """run.json as a dict, or None when it does not exist. Raises CoreError when corrupt."""
    return _read_json(_run_path(), "run")


def save_run(run: dict) -> None:
    _write_json(_run_path(), run, "run")


def run_day() -> str:
    """The date of run.json's `started`, else today: a run crossing midnight keeps one day."""
    run = load_run()
    return run["started"][:10] if run else today_utc()


def facts_path(day=None) -> pathlib.Path:
    return state_dir() / f"facts-{day or run_day()}.json"


def load_rules() -> dict:
    return json.loads((ROOT / "data" / "rules.json").read_text(encoding="utf-8"))


def load_facts(path) -> list:
    """The facts in path; [] when missing. Raises CoreError when corrupt."""
    data = _read_json(path, "facts")
    return data["facts"] if data else []


def add_facts(new: list, path=None) -> None:
    """Merge new facts by (subject, field): later fetched_at wins, a tie goes to the new one."""
    path = facts_path() if path is None else pathlib.Path(path)
    merged = {(f["subject"], f["field"]): f for f in load_facts(path)}
    for item in new:
        if not isinstance(item, dict) or not {"subject", "field", "fetched_at"} <= item.keys():
            raise CoreError(f"not a fact: {item!r}")
        key = (item["subject"], item["field"])
        old = merged.get(key)
        if old is None or item["fetched_at"] >= old["fetched_at"]:
            merged[key] = item
    facts = [merged[k] for k in sorted(merged)]
    _write_json(path, {"schema": 1, "facts": facts}, "facts")


def fact(subject, field, value, source, by="script", to_verify=None) -> dict:
    """One fact stamped now_utc(); with to_verify, value is None (never a guess)."""
    item = {"subject": subject, "field": field, "value": value, "source": source,
            "fetched_at": now_utc(), "by": by}
    if to_verify is not None:
        item["value"] = None
        item["to_verify"] = to_verify
    return item


def meter(script_calls: int = 1, github_points: int = 0, questions_asked: int = 0, partial=None) -> None:
    """Add counts to run.json, creating it (as `run.py start` would) when missing."""
    counts = {"script_calls": script_calls, "github_points": github_points,
              "questions_asked": questions_asked}
    for name, value in counts.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise CoreError(f"meter: {name} must be a non-negative integer, got {value!r}")
    run = load_run() or new_run()
    for name, value in counts.items():
        run[name] += value
    if partial is not None:
        run["partial"] = bool(partial)
    save_run(run)


def emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def utf8_stdout() -> None:
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

"""Shared core for every stack-scout script: clock, token, redaction, facts file, run meter.

State lives in state_dir(): run.json (the run meter) and facts-<run day>.json.
Files that exist but are not valid JSON, or do not pass their schema, raise
CoreError (a ValueError); a script catches it, prints {"ok": false, "error": ...}
and exits EXIT_BLOCKED. Nothing here prints or stores the GitHub token.

Every read-merge-write runs under locked(): a `.lock` file next to the target,
created with O_CREAT|O_EXCL, waited for up to LOCK_WAIT seconds, and removed
when older than LOCK_STALE seconds. Windows refuses os.replace onto a file
another process is reading, so reads and replaces retry on PermissionError for
up to RETRY_FOR seconds before giving up with CoreError.
"""
import contextlib
import datetime
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import schema

ROOT = pathlib.Path(__file__).resolve().parent.parent

EXIT_OK = 0
EXIT_BLOCKED = 2
EXIT_RATE_LIMITED = 3

_STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

LOCK_WAIT = 10.0   # seconds to wait for another process's lock
LOCK_STALE = 30.0  # a lock older than this was left by a crashed process
RETRY_FOR = 2.0    # seconds to keep retrying a read or replace on PermissionError
_PAUSE = 0.05


class CoreError(ValueError):
    """Bad state or settings: a script reports it as JSON and exits EXIT_BLOCKED."""


def _retry(action, what):
    """Run action(), retrying PermissionError (Windows sharing clashes) for RETRY_FOR seconds."""
    for _ in range(int(RETRY_FOR / _PAUSE)):
        try:
            return action()
        except PermissionError:
            time.sleep(_PAUSE)
    try:
        return action()
    except PermissionError as exc:
        raise CoreError(f"{what}: still busy after {RETRY_FOR} s: {exc.strerror or exc}") from None


def _stale(path) -> bool:
    try:
        return time.time() - os.path.getmtime(path) > LOCK_STALE
    except OSError:
        return False


def _put_back(side, lock) -> bool:
    """Move side back to lock only if no lock exists now (never overwrite one)."""
    try:
        if os.name == "nt":
            os.rename(side, lock)  # fails when lock exists
        else:
            os.link(side, lock)  # fails when lock exists
            os.unlink(side)
        return True
    except OSError:
        return False


def _break_stale(lock) -> bool:
    """Remove lock if it is stale, without ever removing a fresh one.

    The lock is first renamed to a unique side name, so only one waiter gets
    it; the renamed file is checked again, because another waiter may have
    broken the old lock and taken a fresh one since our first look. A fresh
    one is put back (when the name is free); if it cannot be, it is left as a
    side file and nothing is deleted. Returns True only when a stale lock was
    removed, so the caller retries at once; otherwise it waits as usual.
    """
    side = lock.with_name(f"{lock.name}.{os.getpid()}-{secrets.token_hex(6)}")
    try:
        os.rename(lock, side)
    except OSError:
        return False  # gone already, renamed by another waiter, or not ours to move
    if _stale(side):
        try:
            os.unlink(side)
            return True
        except OSError:
            return False
    _put_back(side, lock)
    return False


def _clean_side_files(folder) -> None:
    """Remove .lock.* side files left by crashed waiters, once older than LOCK_STALE."""
    for side in folder.glob(".lock.*"):
        if _stale(side):
            try:
                os.unlink(side)
            except OSError:
                pass


@contextlib.contextmanager
def locked(folder=None):
    """Hold folder/.lock (default: state_dir()) for one read-merge-write.

    The lock file holds a nonce (pid + random hex); release deletes it only
    while it still holds our nonce, so a holder paused past LOCK_STALE never
    deletes a successor's lock. Not re-entrant: calling meter(), add_facts()
    or locked() on the same folder inside `with locked()` waits LOCK_WAIT
    seconds and fails with CoreError. Staleness compares the file's mtime with
    this machine's clock, so a state dir on a network share whose clock is
    skewed by more than LOCK_STALE seconds may see live locks as stale (or
    dead ones as fresh for longer). A folder where the lock cannot be created
    for any reason but a held lock raises CoreError at once.
    """
    folder = pathlib.Path(folder) if folder is not None else state_dir()
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / ".lock"
    nonce = f"{os.getpid()}-{secrets.token_hex(8)}"
    deadline = time.monotonic() + LOCK_WAIT
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):
            if _stale(lock) and _break_stale(lock):
                continue
            if time.monotonic() >= deadline:
                raise CoreError(f"could not take the lock {lock.name} in {folder} "
                                f"within {LOCK_WAIT} s") from None
            time.sleep(_PAUSE)
            continue
        except OSError as exc:
            raise CoreError(f"cannot create the lock {lock.name} in {folder}: {exc}") from None
        try:
            os.write(fd, nonce.encode("ascii"))
        except OSError as exc:
            os.close(fd)
            try:
                os.unlink(lock)
            except OSError:
                pass
            raise CoreError(f"cannot write the lock {lock.name} in {folder}: {exc}") from None
        os.close(fd)
        break
    _clean_side_files(folder)
    try:
        yield
    finally:
        try:
            if _retry(lambda: lock.read_text(encoding="ascii"), "reading the lock") == nonce:
                _retry(lambda: os.unlink(lock), "removing the lock")
        except (OSError, ValueError):
            pass  # gone or replaced: not ours to remove


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
        proc = subprocess.run(["gh", "auth", "token"], stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=5)
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
        text = _retry(lambda: path.read_text(encoding="utf-8-sig"), f"reading {path.name}")
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
        _retry(lambda: os.replace(tmp, path), f"writing {path.name}")
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
    """data/rules.json; CoreError when it is missing or not a JSON object."""
    try:
        rules = json.loads((ROOT / "data" / "rules.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CoreError(f"cannot load rules.json: {exc}") from None
    if not isinstance(rules, dict):
        raise CoreError("rules.json is not a JSON object")
    return rules


def load_facts(path) -> list:
    """The facts in path; [] when missing. Raises CoreError when corrupt."""
    data = _read_json(path, "facts")
    return data["facts"] if data else []


def add_facts(new: list, path=None) -> None:
    """Merge new facts by (subject, field): later fetched_at wins, a tie goes to the new one."""
    path = facts_path() if path is None else pathlib.Path(path)
    item_schema = schema.load("facts")["properties"]["facts"]["items"]
    for i, item in enumerate(new):
        errors = schema.validate(item, item_schema)
        if errors:  # name the keys only: a bad item's values may hold a secret
            keys = sorted(map(str, item)) if isinstance(item, dict) else type(item).__name__
            raise CoreError(f"fact {i} is invalid ({'; '.join(errors[:3])}); its keys: {keys}")
    with locked(path.parent):
        merged = {(f["subject"], f["field"]): f for f in load_facts(path)}
        for item in new:
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
    with locked():
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


# HTTP: one client for GitHub, OSV and deps.dev, with back-off on rate limits (T5)

def github_api() -> str:
    """Return the GitHub API base URL (read at call time)."""
    return os.environ.get("STACK_SCOUT_GITHUB_API", "https://api.github.com")


def osv_api() -> str:
    """Return the OSV API base URL (read at call time)."""
    return os.environ.get("STACK_SCOUT_OSV_API", "https://api.osv.dev")


def depsdev_api() -> str:
    """Return the deps.dev API base URL (read at call time)."""
    return os.environ.get("STACK_SCOUT_DEPSDEV_API", "https://api.deps.dev")


class RateLimited(Exception):
    """Raised when rate limit is hit and retries exhausted or wait would exceed 60 s."""

    def __init__(self, status: int, reset_at: float | int | None = None, message: str = "rate limited"):
        super().__init__(message)
        self.status = status
        self.reset_at = reset_at


def http_json(
    method: str,
    url: str,
    body: dict | None = None,
    token: str | None = None,
    retries: int = 3,
) -> tuple[int, dict | list | None]:
    """
    Perform an HTTP request with JSON request/response, retrying on rate limits.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: Full request URL.
        body: Optional JSON-serializable request body.
        token: Optional bearer token for Authorization header.
        retries: Number of retries on rate limit (total requests = retries + 1).

    Returns:
        (status_code, parsed_json_or_None) for 2xx and 404.

    Raises:
        RateLimited: Rate limit hit and retries exhausted or wait > 60 s.
        RuntimeError: Other HTTP errors or network failures (token redacted).
    """
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "User-Agent": "stack-scout",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                status = resp.getcode()
                if not raw:
                    return status, None
                try:
                    return status, json.loads(raw.decode())
                except ValueError:  # not JSON, or not UTF-8
                    return status, None

        except urllib.error.HTTPError as e:
            status = e.code
            hdrs = e.headers
            raw = e.read() or b""
            body_preview = raw[:300].decode(errors="replace")

            # Rate limit: 429 or 403 with x-ratelimit-remaining == "0"
            is_rate_limit = status == 429 or (
                status == 403 and hdrs.get("x-ratelimit-remaining") == "0"
            )

            if is_rate_limit:
                # Determine wait time and reset_at
                retry_after = hdrs.get("Retry-After")
                reset_at = None
                wait = 0.0

                if retry_after is not None:
                    try:
                        seconds = float(retry_after)
                    except ValueError:  # an HTTP date: fall back to the other headers
                        seconds = -1.0
                    if 0 <= seconds < float("inf"):  # also rejects nan
                        wait = seconds
                        reset_at = time.time() + wait

                if reset_at is None:  # no usable Retry-After
                    reset_header = hdrs.get("x-ratelimit-reset")
                    if reset_header is not None:
                        try:
                            reset_epoch = float(reset_header)
                            reset_at = reset_epoch
                            wait = max(0.0, reset_epoch - time.time())
                        except ValueError:
                            pass

                if reset_at is None:  # neither header: back off 2, 4, 8 s
                    wait = 2 ** (attempt + 1)  # 2, 4, 8, ...

                # If wait > 60 s, raise immediately without sleeping
                if wait > 60:
                    raise RateLimited(status, reset_at)

                # If we have retries left, sleep and continue
                if attempt < retries:
                    if os.environ.get("STACK_SCOUT_NO_SLEEP") != "1":
                        time.sleep(wait)
                    continue

                # Retries exhausted
                raise RateLimited(status, reset_at)

            # 404 is not an error for this function
            if status == 404:
                if not raw:
                    return 404, None
                try:
                    return 404, json.loads(raw.decode())
                except ValueError:  # not JSON, or not UTF-8
                    return 404, None

            # Other HTTP errors
            raise RuntimeError(redact(f"{method} {url} -> HTTP {status}: {body_preview}", token))

        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason = getattr(e, "reason", str(e))
            raise RuntimeError(redact(f"{method} {url} failed: {reason}", token))

    raise AssertionError("unreachable")  # every pass of the loop returns, retries or raises

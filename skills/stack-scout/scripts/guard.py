"""The search guard: names from the SOW never reach a web search.

  python guard.py terms --sow FILE [--private-terms FILE] [--answers FILE]
      writes terms.json in the state folder; prints {"ok": true, "private": N, "extracted": N} (counts only)
  python guard.py check "<query>"
      prints {"ok": true} (exit 0), or {"ok": false, "hits": [...]} (exit 2)

Private terms (typed by the user) always block, even when they are also technology names. Terms extracted
from the SOW (capitalised words and runs of them that are not common English or technology names) block
unless they are technology names. A false positive only makes a query more generic; a false negative leaks,
so when unsure, block. Never prints the SOW text.
"""
import json
import pathlib
import re
import sys

import common

DEFAULT_OPTIONS = ["None", "I'll type them"]
WORD = r"[A-Z][A-Za-z0-9&'.-]*"
ACRONYM = re.compile(r"[A-Z]{2,6}")


def load_words(name) -> set:
    """Lower-cased lines of data/<name>, without blank lines and # comments."""
    text = (common.ROOT / "data" / name).read_text(encoding="utf-8")
    return {line.strip().lower() for line in text.splitlines() if line.strip() and not line.startswith("#")}


def _clean(word: str) -> str:
    return word[:-1] if word.endswith(".") else word


def _keep(term: str, common_words: set, tech: set) -> bool:
    low = term.lower()
    if ACRONYM.fullmatch(term):
        return low not in tech
    return low not in common_words and low not in tech


def extract_terms(sow_text: str, common_words: set, tech: set) -> set:
    """Capitalised words, and runs of 2+ of them within a sentence, that are not common or tech words."""
    found = set()
    for match in re.finditer(rf"{WORD}(?: {WORD})*", sow_text):
        run, words = [], match.group(0).split(" ")
        for i, raw in enumerate(words):
            run.append(_clean(raw))
            if raw.endswith(".") or i == len(words) - 1:  # a full stop ends the sentence, and the run
                for start in range(len(run)):
                    for end in range(start + 1, len(run) + 1):
                        term = " ".join(run[start:end])
                        if term and _keep(term, common_words, tech):
                            found.add(term)
                run = []
    return found


def _hits(query: str, term: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", query, re.IGNORECASE) is not None


def check(query: str, private: set, extracted: set, tech: set) -> list:
    """The terms the query would leak; empty when it may be searched."""
    hits = [t for t in sorted(private) if _hits(query, t)]
    hits += [t for t in sorted(extracted) if t.lower() not in tech and t not in hits and _hits(query, t)]
    return hits


def private_from_answers(answers: dict, options: list) -> set:
    """Names typed for the private_names question; the question's own option labels never count."""
    value = answers.get("private_names") or ""
    if isinstance(value, list):
        value = ",".join(str(v) for v in value)
    labels = {o.lower() for o in options}
    parts = (p.strip() for p in re.split(r"[,;]", str(value)))
    return {p for p in parts if p and p.lower() not in labels}


def _options() -> list:
    try:
        questions = json.loads((common.ROOT / "questions.json").read_text(encoding="utf-8"))["questions"]
        question = next(q for q in questions if q.get("id") == "private_names")
        return [o["label"] for o in question["options"]] or DEFAULT_OPTIONS
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return DEFAULT_OPTIONS


def _read(path: str) -> str:
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise common.CoreError(f"cannot read {path}: {type(exc).__name__}") from None


def _terms(args) -> dict:
    opts = {}
    while args:
        flag = args.pop(0)
        if flag not in ("--sow", "--private-terms", "--answers") or not args or flag in opts:
            raise common.CoreError("usage: guard.py terms --sow FILE [--private-terms FILE] [--answers FILE]")
        opts[flag] = args.pop(0)
    if "--sow" not in opts:
        raise common.CoreError("terms needs --sow FILE")
    private = set()
    if "--private-terms" in opts:
        lines = _read(opts["--private-terms"]).splitlines()
        private |= {l.strip() for l in lines if l.strip() and not l.strip().startswith("#")}
    if "--answers" in opts:
        try:
            answers = json.loads(_read(opts["--answers"]))
        except ValueError:
            raise common.CoreError("--answers is not valid JSON") from None
        if not isinstance(answers, dict):
            raise common.CoreError("--answers must be a JSON object")
        private |= private_from_answers(answers, _options())
    extracted = extract_terms(_read(opts["--sow"]), load_words("common-words.txt"), load_words("tech-terms.txt"))
    data = {"private": sorted(private), "extracted": sorted(extracted)}
    (common.state_dir() / "terms.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "private": len(private), "extracted": len(extracted)}


def _check(query: str):
    path = common.state_dir() / "terms.json"
    if not path.exists():
        return {"ok": False, "error": "run guard.py terms first"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        private, extracted = set(data["private"]), set(data["extracted"])
    except (ValueError, KeyError, TypeError):
        raise common.CoreError("terms.json is damaged: run guard.py terms again") from None
    hits = check(query, private, extracted, load_words("tech-terms.txt"))
    return {"ok": True} if not hits else {"ok": False, "hits": hits}


def main(argv) -> int:
    common.utf8_stdout()
    try:
        common.meter(script_calls=1)
        if argv[:1] == ["terms"]:
            out = _terms(list(argv[1:]))
        elif len(argv) == 2 and argv[0] == "check":
            out = _check(argv[1])
        else:
            raise common.CoreError('usage: guard.py terms --sow FILE ... | check "<query>"')
    except (common.CoreError, OSError) as exc:
        out = {"ok": False, "error": str(exc)}
    common.emit(out)
    return common.EXIT_OK if out.get("ok") else common.EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""The run's start and end. Only this script resets run.json.

  python run.py start            fresh run.json; prints {"ok": true, "day": "<run day>"}
  python run.py questions N      sets questions_asked to N; prints {"ok": true, "questions_asked": N}
  python run.py end [--partial]  sets ended (and partial); prints the whole run.json

`questions` and `end` create run.json first when it is missing. Bad arguments,
a corrupt run.json (except for `start`, which replaces it) or a bad
STACK_SCOUT_NOW print {"ok": false, "error": "..."} and exit 2.
run.py itself is not metered (no script call is counted): it controls the meter.
N must be ASCII digits and at most rules.json's max_questions.
"""
import sys

import common

USAGE = "usage: run.py start | questions N | end [--partial]"


def _count(text):
    cap = common.load_rules()["max_questions"]
    if not (0 < len(text) <= 4 and text.isascii() and text.isdigit()) or int(text) > cap:
        raise common.CoreError(f"questions needs a whole number from 0 to {cap}, got {text[:20]!r}")
    return int(text)


def _main(argv):
    if argv == ["start"]:
        run = common.new_run()
        with common.locked():
            common.save_run(run)
        return {"ok": True, "day": run["started"][:10]}
    if len(argv) == 2 and argv[0] == "questions":
        n = _count(argv[1])
        with common.locked():
            run = common.load_run() or common.new_run()
            run["questions_asked"] = n
            common.save_run(run)
        return {"ok": True, "questions_asked": n}
    if argv[:1] == ["end"] and argv[1:] in ([], ["--partial"]):
        with common.locked():
            run = common.load_run() or common.new_run()
            run["ended"] = common.now_utc()
            if argv[1:]:
                run["partial"] = True
            common.save_run(run)
        return run
    raise common.CoreError(USAGE)


def main(argv):
    common.utf8_stdout()
    try:
        out = _main(argv)
    except (common.CoreError, OSError) as exc:
        common.emit({"ok": False, "error": str(exc)})
        return common.EXIT_BLOCKED
    common.emit(out)
    return common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

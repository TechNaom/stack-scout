"""Shared test helpers: repository paths and temporary folders."""
import atexit
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "stack-scout"

_scripts = str(SKILL / "scripts")
if sys.path[:1] != [_scripts]:
    sys.path.insert(0, _scripts)


def tmpdir() -> pathlib.Path:
    """Return a new temporary folder that is removed when Python exits."""
    path = pathlib.Path(tempfile.mkdtemp(prefix="stack-scout-test-"))
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    return path

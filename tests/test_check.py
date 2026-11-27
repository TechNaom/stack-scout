"""tests/check.py must fail cleanly (FAIL lines, exit 1, no traceback) on bad manifests."""
import json
import os
import shutil
import subprocess
import sys
import unittest

from tests import helpers


def _copy_repo():
    root = helpers.tmpdir()
    shutil.copytree(helpers.ROOT / ".claude-plugin", root / ".claude-plugin")
    shutil.copy2(helpers.ROOT / "LICENSE", root / "LICENSE")
    (root / "tests").mkdir()
    shutil.copy2(helpers.ROOT / "tests" / "check.py", root / "tests" / "check.py")
    return root


def _run(root):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    return subprocess.run(
        [sys.executable, str(root / "tests" / "check.py")],
        capture_output=True,
        env=env,
        timeout=60,
    )


def _edit(path, change):
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class CheckScriptTest(unittest.TestCase):
    def assert_fails_cleanly(self, root):
        result = _run(root)
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        self.assertEqual(result.returncode, 1, stdout + stderr)
        self.assertIn("FAIL:", stdout)
        self.assertNotIn("Traceback", stderr)

    def test_good_copy_passes(self):
        result = _run(_copy_repo())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok: 7 checks", result.stdout.decode("utf-8"))

    def test_missing_plugin_json(self):
        root = _copy_repo()
        (root / ".claude-plugin" / "plugin.json").unlink()
        self.assert_fails_cleanly(root)

    def test_plugins_is_dict(self):
        root = _copy_repo()
        _edit(root / ".claude-plugin" / "marketplace.json", lambda d: d.update(plugins={"a": 1}))
        self.assert_fails_cleanly(root)

    def test_plugins_is_number(self):
        root = _copy_repo()
        _edit(root / ".claude-plugin" / "marketplace.json", lambda d: d.update(plugins=5))
        self.assert_fails_cleanly(root)

    def test_metadata_is_string(self):
        root = _copy_repo()
        _edit(root / ".claude-plugin" / "marketplace.json", lambda d: d.update(metadata="x"))
        self.assert_fails_cleanly(root)

    def test_version_is_list(self):
        root = _copy_repo()
        _edit(root / ".claude-plugin" / "plugin.json", lambda d: d.update(version=[1]))
        self.assert_fails_cleanly(root)

    def test_version_is_dict(self):
        root = _copy_repo()
        _edit(root / ".claude-plugin" / "plugin.json", lambda d: d.update(version={"v": 1}))
        self.assert_fails_cleanly(root)

    def test_name_with_cjk_character(self):
        root = _copy_repo()
        _edit(root / ".claude-plugin" / "plugin.json", lambda d: d.update(name="stack-\u5b57"))
        self.assert_fails_cleanly(root)


if __name__ == "__main__":
    unittest.main()

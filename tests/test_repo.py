"""Repository basics: CI workflow shape."""
import unittest

from tests import helpers


class RepoTest(unittest.TestCase):
    def test_ci_matrix(self):
        text = (helpers.ROOT / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")
        for needle in (
            "ubuntu-latest",
            "windows-latest",
            "macos-latest",
            '"3.10"',
            '"3.12"',
            "python -m unittest discover -s tests -t . -v",
            "python tests/check.py",
        ):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

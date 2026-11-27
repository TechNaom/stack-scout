"""The shared core (scripts/common.py) and the run start and end (scripts/run.py).

Every test fixes the clock with STACK_SCOUT_NOW, keeps its state in a fresh
STACK_SCOUT_DIR and turns off `gh` with STACK_SCOUT_NO_GH=1.
"""
import json
import os
import subprocess
import sys
import unittest

from tests import helpers
import common
import schema

RUN = helpers.SKILL / "scripts" / "run.py"
NOW = "2026-11-27T10:00:00Z"
TOKEN = "fake-token-123"


def _fact(subject="github:a/b", field="stars", value=1, at=NOW, **extra):
    item = {"subject": subject, "field": field, "value": value,
            "source": "https://api.github.com/repos/a/b", "fetched_at": at, "by": "script"}
    item.update(extra)
    return item


class CoreTest(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.dir = helpers.tmpdir()
        os.environ["STACK_SCOUT_DIR"] = str(self.dir)
        os.environ["STACK_SCOUT_NOW"] = NOW
        os.environ["STACK_SCOUT_NO_GH"] = "1"
        os.environ.pop("GITHUB_TOKEN", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def run_py(self, *args):
        proc = subprocess.run(
            [sys.executable, str(RUN), *args], capture_output=True,
            text=True, encoding="utf-8", env=dict(os.environ), timeout=60,
        )
        self.assertNotIn("Traceback", proc.stderr)
        return proc.returncode, json.loads(proc.stdout)

    def read_run(self):
        return json.loads((self.dir / "run.json").read_text(encoding="utf-8"))

    def assert_valid(self, name, instance):
        self.assertEqual(schema.validate(instance, schema.load(name)), [])


class ClockTest(CoreTest):
    def test_fixed_clock(self):
        self.assertEqual(common.now_utc(), NOW)
        self.assertEqual(common.today_utc(), "2026-11-27")

    def test_real_clock_shape(self):
        del os.environ["STACK_SCOUT_NOW"]
        self.assertRegex(common.now_utc(), r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")

    def test_bad_clock_fails_clearly(self):
        for bad in ("2026-11-27 10:00:00", "2026-11-27T10:00:00Z\n", "2026-13-01T10:00:00Z", "x"):
            os.environ["STACK_SCOUT_NOW"] = bad
            with self.assertRaisesRegex(common.CoreError, "STACK_SCOUT_NOW"):
                common.now_utc()

    def test_exit_codes(self):
        self.assertEqual((common.EXIT_OK, common.EXIT_BLOCKED, common.EXIT_RATE_LIMITED), (0, 2, 3))


class StateDirTest(CoreTest):
    def test_env_dir_created(self):
        target = self.dir / "nested" / "state"
        os.environ["STACK_SCOUT_DIR"] = str(target)
        self.assertEqual(common.state_dir(), target)
        self.assertTrue(target.is_dir())

    def test_default_dir(self):
        del os.environ["STACK_SCOUT_DIR"]
        cwd = os.getcwd()
        os.chdir(self.dir)
        try:
            self.assertEqual(common.state_dir().resolve(), (self.dir / ".stack-scout").resolve())
            self.assertTrue((self.dir / ".stack-scout").is_dir())
        finally:
            os.chdir(cwd)


class TokenTest(CoreTest):
    def test_token_from_env(self):
        os.environ["GITHUB_TOKEN"] = TOKEN
        self.assertEqual(common.get_token(), TOKEN)

    def test_no_token(self):
        self.assertIsNone(common.get_token())

    def test_empty_token_is_no_token(self):
        for empty in ("", "   "):
            os.environ["GITHUB_TOKEN"] = empty
            self.assertIsNone(common.get_token())

    def test_missing_gh_gives_none(self):
        del os.environ["STACK_SCOUT_NO_GH"]
        os.environ["PATH"] = str(self.dir)
        self.assertIsNone(common.get_token())

    def test_redact(self):
        self.assertEqual(common.redact(f"a {TOKEN} b {TOKEN}", TOKEN), "a *** b ***")
        self.assertEqual(common.redact("abc", None), "abc")
        self.assertEqual(common.redact("abc", ""), "abc")


class FactsTest(CoreTest):
    def test_fact_builder(self):
        f = common.fact("github:a/b", "stars", 5, "https://api.github.com/repos/a/b")
        self.assertEqual(f, _fact(value=5))
        g = common.fact("github:a/b", "licence", "MIT", "https://x.test/", by="model-read",
                        to_verify="read the LICENSE file")
        self.assertIsNone(g["value"])
        self.assertEqual(g["to_verify"], "read the LICENSE file")
        self.assertEqual(g["by"], "model-read")

    def test_missing_file_is_empty(self):
        self.assertEqual(common.load_facts(self.dir / "nope.json"), [])

    def test_merge_newer_wins_and_tie_goes_to_new(self):
        path = self.dir / "f.json"
        common.add_facts([_fact(value=1, at="2026-11-27T10:00:00Z"),
                          _fact(field="archived", value=False, at="2026-11-27T10:00:00Z")], path)
        common.add_facts([_fact(value=2, at="2026-11-27T09:00:00Z")], path)  # older: ignored
        self.assertEqual({f["field"]: f["value"] for f in common.load_facts(path)},
                         {"stars": 1, "archived": False})
        common.add_facts([_fact(value=3, at="2026-11-27T10:00:00Z")], path)  # tie: new wins
        common.add_facts([_fact(field="archived", value=True, at="2026-11-27T11:00:00Z")], path)
        self.assertEqual({f["field"]: f["value"] for f in common.load_facts(path)},
                         {"stars": 3, "archived": True})

    def test_merge_within_one_call(self):
        path = self.dir / "f.json"
        common.add_facts([_fact(value=1, at="2026-11-27T11:00:00Z"),
                          _fact(value=2, at="2026-11-27T10:00:00Z")], path)
        self.assertEqual([f["value"] for f in common.load_facts(path)], [1])

    def test_file_shape_sorted_and_valid(self):
        path = self.dir / "f.json"
        common.add_facts([_fact(subject="github:z/z", field="a"), _fact(subject="github:a/a", field="b"),
                          _fact(subject="github:a/a", field="a", value="é")], path)
        raw = path.read_bytes()
        self.assertNotIn(b"\r\n", raw)
        data = json.loads(raw.decode("utf-8"))
        self.assert_valid("facts", data)
        self.assertEqual(data["schema"], 1)
        self.assertEqual([(f["subject"], f["field"]) for f in data["facts"]],
                         [("github:a/a", "a"), ("github:a/a", "b"), ("github:z/z", "a")])
        self.assertIn("é".encode("utf-8"), raw)
        self.assertEqual(raw.decode("utf-8"), json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["f.json"])  # no temp left

    def test_invalid_fact_not_written(self):
        path = self.dir / "f.json"
        common.add_facts([_fact()], path)
        before = path.read_bytes()
        with self.assertRaises(common.CoreError):
            common.add_facts([_fact(subject="https://github.com/a/b")], path)
        self.assertEqual(path.read_bytes(), before)

    def test_corrupt_facts_file(self):
        path = self.dir / "f.json"
        for text in ("{not json", "[]", '{"schema": 1, "facts": [{"subject": "x"}]}'):
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(common.CoreError):
                common.load_facts(path)
            with self.assertRaises(common.CoreError):
                common.add_facts([_fact()], path)

    def test_default_facts_path(self):
        self.assertEqual(common.facts_path(), self.dir / "facts-2026-11-27.json")
        self.assertEqual(common.facts_path("2026-01-02"), self.dir / "facts-2026-01-02.json")
        common.add_facts([_fact()])
        self.assertEqual(len(common.load_facts(common.facts_path())), 1)


class RulesTest(CoreTest):
    def test_rules(self):
        rules = common.load_rules()
        self.assertEqual(set(rules), {"dead_after_months", "relicence_window_months", "tool_call_cap",
                                      "max_questions", "bot_window_commits", "required_fields",
                                      "bot_logins"})
        self.assertEqual(rules["tool_call_cap"], 200)
        self.assertEqual(rules["max_questions"], 8)
        self.assertEqual(rules["required_fields"],
                         ["exists", "stars", "licence", "last_activity", "archived", "latest_release"])
        self.assertIn("dependabot", rules["bot_logins"])


class MeterTest(CoreTest):
    def test_meter_twice(self):
        common.meter()
        os.environ["STACK_SCOUT_NOW"] = "2026-11-27T10:05:00Z"
        common.meter(github_points=3, questions_asked=1, partial=True)
        run = self.read_run()
        self.assert_valid("run", run)
        self.assertEqual(run["script_calls"], 2)
        self.assertEqual(run["started"], NOW)
        self.assertEqual(run["github_points"], 3)
        self.assertEqual(run["questions_asked"], 1)
        self.assertIs(run["partial"], True)
        common.meter()
        self.assertIs(self.read_run()["partial"], True)  # None leaves it alone
        self.assertNotIn(b"\r\n", (self.dir / "run.json").read_bytes())

    def test_meter_rejects_negative(self):
        with self.assertRaises(common.CoreError):
            common.meter(script_calls=-1)
        self.assertFalse((self.dir / "run.json").exists())

    def test_run_crossing_midnight_keeps_its_day(self):
        os.environ["STACK_SCOUT_NOW"] = "2026-11-27T23:59:00Z"
        common.meter()
        os.environ["STACK_SCOUT_NOW"] = "2026-11-28T00:01:00Z"
        self.assertEqual(common.run_day(), "2026-11-27")
        self.assertEqual(common.facts_path().name, "facts-2026-11-27.json")

    def test_corrupt_run_json(self):
        for text in ("{oops", "[]", '{"schema": 1}'):
            (self.dir / "run.json").write_text(text, encoding="utf-8")
            with self.assertRaises(common.CoreError):
                common.meter()
            with self.assertRaises(common.CoreError):
                common.run_day()


class RunScriptTest(CoreTest):
    def test_start_questions_end(self):
        self.assertEqual(self.run_py("start"), (0, {"ok": True, "day": "2026-11-27"}))
        self.assert_valid("run", self.read_run())
        code, out = self.run_py("questions", "3")
        self.assertEqual(code, 0)
        self.assertEqual(self.read_run()["questions_asked"], 3)
        os.environ["STACK_SCOUT_NOW"] = "2026-11-27T10:30:00Z"
        code, out = self.run_py("end")
        self.assertEqual(code, 0)
        run = self.read_run()
        self.assertEqual(out, run)
        self.assert_valid("run", run)
        self.assertEqual(run["ended"], "2026-11-27T10:30:00Z")
        self.assertEqual(run["questions_asked"], 3)
        self.assertIs(run["partial"], False)

    def test_end_partial(self):
        self.run_py("start")
        code, out = self.run_py("end", "--partial")
        self.assertEqual(code, 0)
        self.assertIs(out["partial"], True)
        self.assert_valid("run", self.read_run())

    def test_second_start_resets(self):
        self.run_py("start")
        common.meter(github_points=5)
        self.run_py("questions", "2")
        self.run_py("end")
        os.environ["STACK_SCOUT_NOW"] = "2026-12-04T08:00:00Z"
        self.assertEqual(self.run_py("start"), (0, {"ok": True, "day": "2026-12-04"}))
        run = self.read_run()
        self.assertEqual(run, {"schema": 1, "started": "2026-12-04T08:00:00Z", "ended": None,
                               "script_calls": 0, "github_points": 0, "questions_asked": 0,
                               "partial": False})
        self.assertEqual(common.facts_path().name, "facts-2026-12-04.json")

    def test_start_replaces_corrupt_run_json(self):
        (self.dir / "run.json").write_text("{oops", encoding="utf-8")
        self.assertEqual(self.run_py("start")[0], 0)
        self.assert_valid("run", self.read_run())

    def test_questions_without_run_json_creates_one(self):
        self.assertEqual(self.run_py("questions", "4")[0], 0)
        run = self.read_run()
        self.assert_valid("run", run)
        self.assertEqual(run["questions_asked"], 4)

    def test_bad_arguments(self):
        self.run_py("start")
        before = (self.dir / "run.json").read_bytes()
        for args in ((), ("nope",), ("questions",), ("questions", "abc"), ("questions", "-1"),
                     ("questions", "1", "2"), ("end", "--full"), ("start", "x")):
            code, out = self.run_py(*args)
            self.assertEqual(code, 2, args)
            self.assertIs(out["ok"], False, args)
            self.assertIsInstance(out["error"], str)
        self.assertEqual((self.dir / "run.json").read_bytes(), before)

    def test_corrupt_run_json_blocks_cleanly(self):
        (self.dir / "run.json").write_text("{oops", encoding="utf-8")
        for args in (("questions", "1"), ("end",)):
            code, out = self.run_py(*args)
            self.assertEqual(code, 2)
            self.assertIs(out["ok"], False)

    def test_bad_clock_blocks_cleanly(self):
        os.environ["STACK_SCOUT_NOW"] = "yesterday"
        code, out = self.run_py("start")
        self.assertEqual(code, 2)
        self.assertIn("STACK_SCOUT_NOW", out["error"])


class EmitTest(CoreTest):
    def test_emit_keeps_unicode(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import common; "
                "common.utf8_stdout(); common.emit({'a': 'é'})")
        proc = subprocess.run([sys.executable, "-c", code, str(helpers.SKILL / "scripts")],
                              capture_output=True, timeout=60)
        self.assertEqual(proc.stdout.decode("utf-8").strip(), '{"a": "é"}')


if __name__ == "__main__":
    unittest.main()

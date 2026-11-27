"""The schema checker and the six hand-written schemas.

Fixtures live in tests/fixtures/schema/:
  <name>.good.json          must give no errors
  <name>.bad-<reason>.json  must give exactly one error, at the path listed
                            for it in BAD below (every bad fixture is listed)
"""
import json
import math
import subprocess
import sys
import unittest

from tests import helpers
import schema

NAMES = ("stack", "facts", "run", "questions", "answers", "labels")
FIXTURES = helpers.ROOT / "tests" / "fixtures" / "schema"
SCRIPT = helpers.SKILL / "scripts" / "schema.py"

# fixture file -> the start of its one expected error ("<path>: ")
BAD = {
    "answers.bad-not-object.json": "$: expected object",
    "answers.bad-number-team_size.json": "$.team_size: expected string",
    "facts.bad-http-source.json": "$.facts[0].source: does not match",
    "facts.bad-missing-fetched_at.json": "$.facts[1].fetched_at: required",
    "facts.bad-unknown-subject.json": "$.facts[0].subject: does not match",
    "facts.bad-wrong-by.json": "$.facts[0].by: not one of",
    "labels.bad-bool-capabilities_min.json": "$[0].capabilities_min: expected integer",
    "labels.bad-unknown-secret.json": "$[0].planted.secret: not allowed",
    "labels.bad-url-fake.json": "$[0].planted.fake[0]: does not match",
    "labels.bad-wrong-format.json": "$[0].format: not one of",
    "questions.bad-one-options.json": "$[0].options: fewer than 2 items",
    "questions.bad-upper-id.json": "$[0].id: does not match",
    "questions.bad-zero-rank.json": "$[0].rank: below minimum 1",
    "run.bad-bool-github_points.json": "$.github_points: expected integer",
    "run.bad-missing-ended.json": "$.ended: required",
    "run.bad-string-script_calls.json": "$.script_calls: expected integer",
    "stack.bad-missing-partial.json": "$.partial: required",
    "stack.bad-missing-reason.json": "$.layers[0].reason: required",
    "stack.bad-missing-why_not.json": "$.layers[0].alternative.why_not: required",
    "stack.bad-url-subject.json": "$.layers[0].projects[0].subject: does not match",
    "stack.bad-wrong-outcome.json": "$.capabilities[0].outcome: not one of",
}


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class SchemaFilesTest(unittest.TestCase):
    def test_every_bad_fixture_has_an_expectation(self):
        found = {p.name for p in FIXTURES.glob("*.bad-*.json")}
        self.assertEqual(found, set(BAD))

    def test_at_least_two_bad_fixtures_per_schema(self):
        for name in NAMES:
            count = sum(1 for f in BAD if f.startswith(f"{name}.bad-"))
            self.assertGreaterEqual(count, 2, name)


def _good_test(name):
    def test(self):
        errors = schema.validate(_read(FIXTURES / f"{name}.good.json"), schema.load(name))
        self.assertEqual(errors, [])
    return test


def _bad_test(name):
    def test(self):
        loaded = schema.load(name)
        for file, expected in sorted(BAD.items()):
            if not file.startswith(f"{name}.bad-"):
                continue
            with self.subTest(file=file):
                errors = schema.validate(_read(FIXTURES / file), loaded)
                self.assertEqual(len(errors), 1, errors)
                self.assertTrue(errors[0].startswith(expected), errors)
    return test


for _name in NAMES:
    setattr(SchemaFilesTest, f"test_{_name}_good", _good_test(_name))
    setattr(SchemaFilesTest, f"test_{_name}_bad", _bad_test(_name))


class ValidateTest(unittest.TestCase):
    def test_unknown_keyword_raises(self):
        with self.assertRaises(ValueError) as ctx:
            schema.validate({}, {"type": "object", "format": "date"})
        self.assertEqual(str(ctx.exception), "unsupported keyword: format")

    def test_unknown_keyword_in_nested_schema_raises(self):
        s = {"type": "object", "properties": {"a": {"oneOf": []}}}
        with self.assertRaises(ValueError):
            schema.validate({"a": 1}, s)

    def test_unknown_keyword_in_items_raises(self):
        with self.assertRaises(ValueError) as ctx:
            schema.validate([], {"type": "array", "items": {"const": 1}})
        self.assertEqual(str(ctx.exception), "unsupported keyword: const")

    def test_unknown_keyword_in_additional_properties_raises(self):
        with self.assertRaises(ValueError) as ctx:
            schema.validate({}, {"additionalProperties": {"minLength": 1}})
        self.assertEqual(str(ctx.exception), "unsupported keyword: minLength")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            schema.validate("x", {"type": "date"})

    def test_bad_keyword_values_raise(self):
        bad = [
            {"required": "a"},
            {"required": [1]},
            {"enum": "a"},
            {"properties": []},
            {"properties": {"a": 1}},
            {"additionalProperties": 0},
            {"additionalProperties": None},
            {"minimum": "1"},
            {"minimum": True},
            {"maximum": None},
            {"minItems": -1},
            {"minItems": 1.0},
            {"minItems": True},
            {"maxItems": "2"},
            {"type": 1},
            {"type": ["string", 1]},
            {"pattern": 1},
            {"pattern": "("},
            {"items": []},
        ]
        for s in bad:
            with self.subTest(schema=s):
                with self.assertRaises(ValueError):
                    schema.validate(None, s)

    def test_bad_keyword_value_raises_even_when_branch_unused(self):
        s = {"type": "object", "properties": {"a": {"pattern": "("}}}
        with self.assertRaises(ValueError):
            schema.validate({}, s)

    def test_bool_is_not_integer_or_number(self):
        self.assertTrue(schema.validate(True, {"type": "integer"}))
        self.assertTrue(schema.validate(False, {"type": "number"}))
        self.assertEqual(schema.validate(3, {"type": "integer"}), [])
        self.assertEqual(schema.validate(3.5, {"type": "number"}), [])
        self.assertEqual(schema.validate(3, {"type": "number"}), [])
        self.assertTrue(schema.validate(3.5, {"type": "integer"}))
        self.assertEqual(schema.validate(True, {"type": "boolean"}), [])

    def test_float_with_zero_fraction_is_not_integer(self):
        self.assertEqual(schema.validate(1.0, {"type": "integer"}), ["$: expected integer"])

    def test_nan_and_infinity_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            for t in ("number", "integer", ["number", "null"]):
                with self.subTest(value=value, type=t):
                    self.assertTrue(schema.validate(value, {"type": t}))

    def test_type_list(self):
        s = {"type": ["number", "null"]}
        self.assertEqual(schema.validate(None, s), [])
        self.assertEqual(schema.validate(1.5, s), [])
        self.assertTrue(schema.validate("x", s))

    def test_reports_every_error_with_path(self):
        s = {
            "type": "object",
            "additionalProperties": False,
            "required": ["layers", "n"],
            "properties": {
                "layers": {
                    "type": "array",
                    "items": {"type": "object", "required": ["reason"]},
                },
                "n": {"type": "integer", "minimum": 1, "maximum": 5},
            },
        }
        errors = schema.validate({"layers": [{}, {"reason": "x"}, {}], "extra": 1}, s)
        self.assertIn("$.layers[0].reason: required", errors)
        self.assertIn("$.layers[2].reason: required", errors)
        self.assertIn("$.n: required", errors)
        self.assertTrue(any(e.startswith("$.extra:") for e in errors), errors)
        self.assertEqual(len(errors), 4, errors)

    def test_odd_keys_are_quoted_in_paths(self):
        s = {"additionalProperties": False}
        self.assertEqual(schema.validate({"a.b": 1}, s), ['$["a.b"]: not allowed'])
        self.assertEqual(schema.validate({"": 1}, s), ['$[""]: not allowed'])
        self.assertEqual(schema.validate({"a\n": 1}, s), ['$["a\\n"]: not allowed'])

    def test_pattern_uses_search_and_enum_min_max(self):
        self.assertEqual(schema.validate("abc", {"pattern": "b"}), [])
        self.assertTrue(schema.validate("abc", {"pattern": "^b$"}))
        self.assertTrue(schema.validate("z", {"enum": ["a", "b"]}))
        self.assertTrue(schema.validate(0, {"minimum": 1}))
        self.assertTrue(schema.validate(9, {"maximum": 5}))
        self.assertTrue(schema.validate([1], {"minItems": 2}))
        self.assertTrue(schema.validate([1, 2, 3], {"maxItems": 2}))

    def test_dollar_does_not_match_before_trailing_newline(self):
        self.assertTrue(schema.validate("ab\n", {"pattern": "^ab$"}))
        self.assertEqual(schema.validate("a$", {"pattern": r"^a\$$"}), [])
        self.assertEqual(schema.validate("$", {"pattern": "^[$]$"}), [])
        run = schema.load("run")
        good = _read(FIXTURES / "run.good.json")
        good["started"] = "2026-01-01T00:00:00Z\n"
        self.assertEqual(len(schema.validate(good, run)), 1)
        stack = schema.load("stack")
        good = _read(FIXTURES / "stack.good.json")
        good["layers"][0]["projects"][0]["subject"] = "github:a/b\n"
        self.assertEqual(len(schema.validate(good, stack)), 1)

    def test_digits_are_ascii_only(self):
        run = schema.load("run")
        good = _read(FIXTURES / "run.good.json")
        good["started"] = "٢٠٢٦-01-01T00:00:00Z"
        self.assertEqual(len(schema.validate(good, run)), 1)

    def test_enum_does_not_confuse_true_and_one(self):
        self.assertTrue(schema.validate(True, {"enum": [1]}))
        self.assertEqual(schema.validate(1, {"enum": [1]}), [])

    def test_enum_exact_number_type(self):
        self.assertTrue(schema.validate(1.0, {"enum": [1]}))
        self.assertTrue(schema.validate(1, {"enum": [1.0]}))

    def test_enum_nested_bool_and_number_differ(self):
        self.assertTrue(schema.validate([1], {"enum": [[True]]}))
        self.assertTrue(schema.validate({"a": 0}, {"enum": [{"a": False}]}))
        self.assertTrue(schema.validate([1], {"enum": [[1, 2]]}))
        self.assertEqual(schema.validate([1, {"a": "x"}], {"enum": [[1, {"a": "x"}]]}), [])

    def test_additional_properties_schema(self):
        s = {"type": "object", "additionalProperties": {"type": "string"}}
        self.assertEqual(schema.validate({"a": "x"}, s), [])
        self.assertEqual(schema.validate({"a": 1}, s)[0].split(":")[0], "$.a")


class LoadTest(unittest.TestCase):
    def test_load_known_names(self):
        for name in NAMES:
            self.assertIsInstance(schema.load(name), dict)

    def test_load_unknown_name_raises(self):
        for name in ("nope", "../x", "stack/../stack", ""):
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as ctx:
                    schema.load(name)
                self.assertIn("unknown schema", str(ctx.exception))


class CliTest(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, encoding="utf-8",
        )

    def _write(self, data):
        path = helpers.tmpdir() / "in.json"
        path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
        return str(path)

    def _invalid(self, *args):
        result = self._run(*args)
        self.assertEqual(result.returncode, 2, result.stderr)
        out = json.loads(result.stdout)
        self.assertIs(out["ok"], False)
        self.assertTrue(out["errors"])
        for e in out["errors"]:
            self.assertTrue(e.startswith("$"), e)
        return out["errors"]

    def test_cli_ok(self):
        result = self._run("answers", str(FIXTURES / "answers.good.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"ok": True})

    def test_cli_invalid(self):
        self._invalid("answers", str(FIXTURES / "answers.bad-not-object.json"))

    def test_cli_usage(self):
        self._invalid("answers")

    def test_cli_unknown_schema(self):
        good = str(FIXTURES / "answers.good.json")
        self.assertIn("unknown schema", self._invalid("nope", good)[0])
        self.assertIn("unknown schema", self._invalid("../x", good)[0])

    def test_cli_missing_file(self):
        self._invalid("answers", str(helpers.tmpdir() / "missing.json"))

    def test_cli_not_json(self):
        self._invalid("answers", self._write("not json"))

    def test_cli_not_utf8(self):
        self._invalid("answers", self._write(b'{"a": "\xff"}'))

    def test_cli_nan_rejected(self):
        text = (FIXTURES / "stack.good.json").read_text(encoding="utf-8")
        text = text.replace('"monthly_estimate": 0', '"monthly_estimate": NaN')
        self.assertIn("NaN", text)
        self._invalid("stack", self._write(text))

    def test_cli_huge_number_rejected(self):
        text = (FIXTURES / "stack.good.json").read_text(encoding="utf-8")
        text = text.replace('"monthly_estimate": 0', '"monthly_estimate": 1e400')
        self._invalid("stack", self._write(text))

    def test_cli_deep_nesting(self):
        self._invalid("answers", self._write("[" * 100000 + "]" * 100000))

    def test_cli_duplicate_key(self):
        errors = self._invalid("answers", self._write('{"x": "a", "x": "b"}'))
        self.assertEqual(errors, ['$: duplicate key "x"'])

    def test_cli_accepts_bom(self):
        path = self._write(b"\xef\xbb\xbf" + (FIXTURES / "answers.good.json").read_bytes())
        result = self._run("answers", path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class MainTest(unittest.TestCase):
    def test_unexpected_error_becomes_json(self):
        import contextlib
        import io
        original = schema.validate

        def boom(instance, s):
            raise RecursionError("too deep")

        schema.validate = boom
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                code = schema.main(["answers", str(FIXTURES / "answers.good.json")])
        finally:
            schema.validate = original
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(out.getvalue()),
            {"ok": False, "errors": ["$: RecursionError: too deep"]},
        )


if __name__ == "__main__":
    unittest.main()

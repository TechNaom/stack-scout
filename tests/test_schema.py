"""The schema checker and the six hand-written schemas.

Fixtures live in tests/fixtures/schema/:
  <name>.good.json          must give no errors
  <name>.bad-<reason>.json  must give at least one error that mentions the
                            last hyphen-separated word of <reason>
                            (stack.bad-missing-reason.json -> "reason")
"""
import json
import subprocess
import sys
import unittest

from tests import helpers
import schema

NAMES = ("stack", "facts", "run", "questions", "answers", "labels")
FIXTURES = helpers.ROOT / "tests" / "fixtures" / "schema"
SCRIPT = helpers.SKILL / "scripts" / "schema.py"


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class SchemaFilesTest(unittest.TestCase):
    pass


def _good_test(name):
    def test(self):
        errors = schema.validate(_read(FIXTURES / f"{name}.good.json"), schema.load(name))
        self.assertEqual(errors, [])
    return test


def _bad_test(name):
    def test(self):
        bads = sorted(FIXTURES.glob(f"{name}.bad-*.json"))
        self.assertGreaterEqual(len(bads), 2, f"need at least 2 bad examples for {name}")
        loaded = schema.load(name)
        for path in bads:
            with self.subTest(file=path.name):
                reason = path.name[len(name) + len(".bad-"):-len(".json")]
                needle = reason.split("-")[-1]
                errors = schema.validate(_read(path), loaded)
                self.assertTrue(errors, f"{path.name} gave no errors")
                self.assertTrue(
                    any(needle in e for e in errors),
                    f"{path.name}: no error mentions {needle!r}: {errors}",
                )
                for e in errors:
                    self.assertTrue(e.startswith("$"), e)
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

    def test_bool_is_not_integer_or_number(self):
        self.assertTrue(schema.validate(True, {"type": "integer"}))
        self.assertTrue(schema.validate(False, {"type": "number"}))
        self.assertEqual(schema.validate(3, {"type": "integer"}), [])
        self.assertEqual(schema.validate(3.5, {"type": "number"}), [])
        self.assertEqual(schema.validate(3, {"type": "number"}), [])
        self.assertTrue(schema.validate(3.5, {"type": "integer"}))
        self.assertEqual(schema.validate(True, {"type": "boolean"}), [])

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

    def test_pattern_uses_search_and_enum_min_max(self):
        self.assertEqual(schema.validate("abc", {"pattern": "b"}), [])
        self.assertTrue(schema.validate("abc", {"pattern": "^b$"}))
        self.assertTrue(schema.validate("z", {"enum": ["a", "b"]}))
        self.assertTrue(schema.validate(0, {"minimum": 1}))
        self.assertTrue(schema.validate(9, {"maximum": 5}))
        self.assertTrue(schema.validate([1], {"minItems": 2}))
        self.assertTrue(schema.validate([1, 2, 3], {"maxItems": 2}))

    def test_enum_does_not_confuse_true_and_one(self):
        self.assertTrue(schema.validate(True, {"enum": [1]}))
        self.assertEqual(schema.validate(1, {"enum": [1]}), [])

    def test_additional_properties_schema(self):
        s = {"type": "object", "additionalProperties": {"type": "string"}}
        self.assertEqual(schema.validate({"a": "x"}, s), [])
        self.assertEqual(schema.validate({"a": 1}, s)[0].split(":")[0], "$.a")


class CliTest(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_cli_ok(self):
        result = self._run("answers", str(FIXTURES / "answers.good.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"ok": True})

    def test_cli_invalid(self):
        bad = sorted(FIXTURES.glob("answers.bad-*.json"))[0]
        result = self._run("answers", str(bad))
        self.assertEqual(result.returncode, 2, result.stderr)
        out = json.loads(result.stdout)
        self.assertIs(out["ok"], False)
        self.assertTrue(out["errors"])


if __name__ == "__main__":
    unittest.main()

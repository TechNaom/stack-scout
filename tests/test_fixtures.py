"""The labelled test SOWs in tests/fixtures/sows/ and their labels.json.

problems(folder) lists everything wrong with one SOW folder; the real folder
must have none, and small broken copies prove each check can fail.
"""
import json
import re
import shutil
import unittest

from tests import helpers
import schema

SOWS = helpers.ROOT / "tests" / "fixtures" / "sows"

# The open-point ids in T10's starter question bank.
OPEN_POINTS = frozenset({"private_names", "distribute", "language", "cloud", "scale", "budget"})

MIN_WORDS, MAX_WORDS = 300, 800

# SOWs must be invented. These are big real brands that are not technology
# products a SOW would name as a tech term (so "AWS", "Azure" or "Postgres"
# are fine). A hit means a real client crept in. Matched as whole words,
# ignoring case. Kept short on purpose: it catches the obvious slip, not all.
# Brands that are also everyday words ("Shell", "Reliance") are left out.
REAL_COMPANIES = (
    "Walmart", "Coca-Cola", "Pepsi", "Nike", "McDonald's", "Toyota", "Unilever",
    "Nestle", "Pfizer", "Maersk", "FedEx", "DHL", "JPMorgan", "Goldman Sachs",
    "Deloitte", "Accenture", "KPMG", "HSBC", "Barclays", "Tesla", "Boeing",
    "Siemens", "Starbucks", "IKEA", "Tata", "Infosys",
)


def _words(text):
    return len(re.findall(r"\S+", text))


def problems(folder):
    """Return every problem with the SOW folder as a list of strings."""
    found = []
    path = folder / "labels.json"
    try:
        labels = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"labels.json cannot be read: {exc}"]
    errors = schema.validate(labels, schema.load("labels"))
    if errors:
        return [f"labels.json: {e}" for e in errors]

    sows = sorted(p.name for p in folder.glob("*.md"))
    counts = {}
    ids = set()
    for label in labels:
        name = label["file"]
        counts[name] = counts.get(name, 0) + 1
        if label["id"] in ids:
            found.append(f"{label['id']}: duplicate id")
        ids.add(label["id"])
        sow = folder / name
        if not sow.is_file():
            found.append(f"{label['id']}: file {name} does not exist")
            continue
        text = sow.read_text(encoding="utf-8")
        if label["format"] != sow.suffix.lstrip("."):
            found.append(f"{label['id']}: format {label['format']} does not match {name}")
        points = label["open_points"]
        unknown = sorted(set(points) - OPEN_POINTS)
        if unknown:
            found.append(f"{label['id']}: unknown open points {unknown}")
        if len(set(points)) != len(points):
            found.append(f"{label['id']}: open point listed twice")
        if not 1 <= len(set(points)) <= 5:
            found.append(f"{label['id']}: needs 1 to 5 open points, has {len(set(points))}")
        if label["capabilities_min"] < 1:
            found.append(f"{label['id']}: capabilities_min must be at least 1")
        client = label["planted"].get("client_name")
        if client is not None and client not in text:
            found.append(f"{label['id']}: client name {client!r} not in {name}")
        words = _words(text)
        if not MIN_WORDS <= words <= MAX_WORDS:
            found.append(f"{name}: {words} words, expected {MIN_WORDS}-{MAX_WORDS}")
        for brand in REAL_COMPANIES:
            if re.search(rf"(?<!\w){re.escape(brand)}(?!\w)", text, re.IGNORECASE):
                found.append(f"{name}: names a real company {brand!r}")
    for name in sows:
        if counts.get(name, 0) != 1:
            found.append(f"{name}: has {counts.get(name, 0)} labels, expected 1")
    return found


class FixturesTest(unittest.TestCase):
    def setUp(self):
        self.labels = json.loads((SOWS / "labels.json").read_text(encoding="utf-8"))

    def test_folder_has_no_problems(self):
        self.assertEqual(problems(SOWS), [])

    def test_the_five_sows(self):
        self.assertEqual(
            sorted(label["file"] for label in self.labels),
            [
                "01-memo-generator.md",
                "02-regulatory-filing.md",
                "03-token-guard.md",
                "04-support-ticket-triage.md",
                "05-document-search.md",
            ],
        )

    def test_planted_is_client_name_only(self):
        for label in self.labels:
            with self.subTest(id=label["id"]):
                self.assertLessEqual(set(label["planted"]), {"client_name"})

    def test_sow_02_plants_a_client_name(self):
        label = next(x for x in self.labels if x["file"] == "02-regulatory-filing.md")
        self.assertTrue(label["planted"].get("client_name"))

    def test_sow_05_states_azure(self):
        label = next(x for x in self.labels if x["file"] == "05-document-search.md")
        text = (SOWS / label["file"]).read_text(encoding="utf-8")
        self.assertIn("must run on Azure", text)
        self.assertNotIn("cloud", label["open_points"])

    def test_each_sow_leaves_a_different_mix_open(self):
        mixes = [frozenset(label["open_points"]) for label in self.labels]
        self.assertEqual(len(set(mixes)), len(mixes))


class ProblemsCatchMistakesTest(unittest.TestCase):
    """Each broken copy of the real folder must give at least one problem."""

    def _copy(self):
        folder = helpers.tmpdir() / "sows"
        shutil.copytree(SOWS, folder)
        labels = json.loads((folder / "labels.json").read_text(encoding="utf-8"))
        return folder, labels

    def _write(self, folder, labels):
        (folder / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")

    def _assert_problem(self, folder, needle):
        found = problems(folder)
        self.assertTrue(any(needle in p for p in found), found)

    def test_missing_labels_file(self):
        folder, _ = self._copy()
        (folder / "labels.json").unlink()
        self._assert_problem(folder, "labels.json cannot be read")

    def test_schema_error(self):
        folder, labels = self._copy()
        labels[0]["format"] = "html"
        self._write(folder, labels)
        self._assert_problem(folder, "labels.json: $[0].format")

    def test_label_file_missing(self):
        folder, labels = self._copy()
        (folder / labels[0]["file"]).unlink()
        self._assert_problem(folder, "does not exist")

    def test_sow_without_label(self):
        folder, labels = self._copy()
        self._write(folder, labels[1:])
        self._assert_problem(folder, f"{labels[0]['file']}: has 0 labels")

    def test_sow_with_two_labels(self):
        folder, labels = self._copy()
        extra = dict(labels[0], id="extra")
        self._write(folder, labels + [extra])
        self._assert_problem(folder, f"{labels[0]['file']}: has 2 labels")

    def test_unknown_open_point(self):
        folder, labels = self._copy()
        labels[0]["open_points"] = labels[0]["open_points"][:1] + ["deadline"]
        self._write(folder, labels)
        self._assert_problem(folder, "unknown open points ['deadline']")

    def test_no_open_points(self):
        folder, labels = self._copy()
        labels[0]["open_points"] = []
        self._write(folder, labels)
        self._assert_problem(folder, "needs 1 to 5 open points")

    def test_client_name_not_in_text(self):
        folder, labels = self._copy()
        labels[0]["planted"] = {"client_name": "Nowhere Holdings"}
        self._write(folder, labels)
        self._assert_problem(folder, "'Nowhere Holdings' not in")

    def test_real_company_name(self):
        folder, labels = self._copy()
        sow = folder / labels[0]["file"]
        sow.write_text(sow.read_text(encoding="utf-8") + "\nShipped via FedEx.\n", encoding="utf-8")
        self._assert_problem(folder, "names a real company 'FedEx'")

    def test_too_short(self):
        folder, labels = self._copy()
        (folder / labels[0]["file"]).write_text("Too short.\n", encoding="utf-8")
        self._assert_problem(folder, "2 words")


if __name__ == "__main__":
    unittest.main()

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

# Formats read as UTF-8 text; the schema also allows docx and pdf.
TEXT_FORMATS = frozenset({"md", "txt"})

# SOWs must be invented. These are big real brands that are not technology
# products a SOW would name as a tech term (so "AWS", "Azure" or "Postgres"
# are fine). A hit means a real client crept in. Matched as whole words,
# ignoring case. Kept short on purpose: it catches the obvious slip, not all.
# Brands that are also everyday words or tech terms ("Shell", "Reliance",
# "Tesla" as in an NVIDIA Tesla GPU or the SI unit) are left out.
REAL_COMPANIES = (
    "Walmart", "Coca-Cola", "Pepsi", "Nike", "McDonald's", "Toyota", "Unilever",
    "Nestle", "Pfizer", "Maersk", "FedEx", "DHL", "JPMorgan", "Goldman Sachs",
    "Deloitte", "Accenture", "KPMG", "HSBC", "Barclays", "Boeing",
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

    # Every file in the folder is a SOW, whatever its format.
    sows = sorted(p.name for p in folder.iterdir() if p.is_file() and p.name != "labels.json")
    counts = {}
    ids = set()
    for label in labels:
        name = label["file"]
        counts[name] = counts.get(name, 0) + 1
        if label["id"] in ids:
            found.append(f"{label['id']}: duplicate id")
        ids.add(label["id"])
        if "/" in name or "\\" in name or name in ("", ".", ".."):
            found.append(f"{label['id']}: file {name!r} must be a plain file name")
            continue
        sow = folder / name
        if not sow.is_file():
            found.append(f"{label['id']}: file {name} does not exist")
            continue
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
        if client is not None and (client.strip() != client or len(client) < 3):
            found.append(f"{label['id']}: client name {client!r} must be at least 3 characters, unpadded")
            client = None
        if label["format"] not in TEXT_FORMATS:
            continue  # docx and pdf need a reader; their text checks come with it
        try:
            text = sow.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            found.append(f"{name} is not UTF-8 text")
            continue
        if client is not None and not re.search(rf"(?<!\w){re.escape(client)}(?!\w)", text):
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
        self.assertEqual(label["planted"].get("client_name"), "Quillmere Haulage")
        text = (SOWS / label["file"]).read_text(encoding="utf-8")
        # The invented name only ever appears whole, so a leak guard looking
        # for the full phrase sees every mention.
        self.assertEqual(text.count("Quillmere"), text.count("Quillmere Haulage"))

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

    def _set(self, change):
        """Copy the folder, apply change(labels[0]) and return the copy."""
        folder, labels = self._copy()
        change(labels[0])
        self._write(folder, labels)
        return folder

    def _append_to_sow(self, folder, extra):
        name = json.loads((folder / "labels.json").read_text(encoding="utf-8"))[0]["file"]
        sow = folder / name
        sow.write_text(sow.read_text(encoding="utf-8") + extra, encoding="utf-8")
        return sow

    def _resize_sow(self, words):
        folder, labels = self._copy()
        (folder / labels[0]["file"]).write_text("word " * words, encoding="utf-8")
        return folder

    def test_duplicate_id(self):
        folder, labels = self._copy()
        labels[1]["id"] = labels[0]["id"]
        self._write(folder, labels)
        self._assert_problem(folder, f"{labels[0]['id']}: duplicate id")

    def test_format_does_not_match_suffix(self):
        folder = self._set(lambda label: label.update(format="txt"))
        self._assert_problem(folder, "format txt does not match")

    def test_open_point_listed_twice(self):
        folder = self._set(lambda label: label.update(open_points=["scale", "scale"]))
        self._assert_problem(folder, "open point listed twice")

    def test_all_six_open_points(self):
        folder = self._set(lambda label: label.update(open_points=sorted(OPEN_POINTS)))
        self._assert_problem(folder, "needs 1 to 5 open points, has 6")

    def test_capabilities_min_zero(self):
        folder = self._set(lambda label: label.update(capabilities_min=0))
        self._assert_problem(folder, "capabilities_min must be at least 1")

    def test_one_word_too_short(self):
        self._assert_problem(self._resize_sow(MIN_WORDS - 1), f"{MIN_WORDS - 1} words")

    def test_one_word_too_long(self):
        self._assert_problem(self._resize_sow(MAX_WORDS + 1), f"{MAX_WORDS + 1} words")

    def test_word_bounds_are_allowed(self):
        for words in (MIN_WORDS, MAX_WORDS):
            with self.subTest(words=words):
                found = problems(self._resize_sow(words))
                self.assertFalse(any(" words, expected" in p for p in found), found)

    def test_real_company_name_any_case(self):
        folder, _ = self._copy()
        self._append_to_sow(folder, "\nShipped via fedex.\n")
        self._assert_problem(folder, "names a real company 'FedEx'")

    def test_tech_terms_are_not_brands(self):
        folder, _ = self._copy()
        self._append_to_sow(folder, "\nRuns on an NVIDIA Tesla T4 near a 3 tesla magnet.\n")
        found = problems(folder)
        self.assertFalse(any("real company" in p for p in found), found)

    # The leak guards in later evals search outgoing queries for the FULL
    # client_name, so the label must hold the whole name exactly as the SOW
    # writes it: no padding, not empty, and not a fragment of a longer word.
    def test_client_name_empty(self):
        folder = self._set(lambda label: label["planted"].update(client_name=""))
        self._assert_problem(folder, "client name '' must be")

    def test_client_name_blank(self):
        folder = self._set(lambda label: label["planted"].update(client_name="  "))
        self._assert_problem(folder, "client name '  ' must be")

    def test_client_name_padded(self):
        folder, labels = self._copy()
        label = next(x for x in labels if x["planted"].get("client_name"))
        label["planted"]["client_name"] = " " + label["planted"]["client_name"]
        self._write(folder, labels)
        self._assert_problem(folder, "must be")

    def test_client_name_partial_word(self):
        folder, labels = self._copy()
        label = next(x for x in labels if x["planted"].get("client_name"))
        label["planted"]["client_name"] = label["planted"]["client_name"][:5]
        self._write(folder, labels)
        self._assert_problem(folder, f"client name {label['planted']['client_name']!r} not in")

    def test_unlabelled_non_md_file(self):
        folder, _ = self._copy()
        (folder / "06-extra.txt").write_text("An extra SOW.\n", encoding="utf-8")
        self._assert_problem(folder, "06-extra.txt: has 0 labels")

    def test_binary_pdf_does_not_crash(self):
        folder, labels = self._copy()
        (folder / "06-scan.pdf").write_bytes(b"%PDF-1.4\n\xff\xfe\x00\x81 binary\n")
        labels.append(dict(labels[0], id="sow-06", file="06-scan.pdf", format="pdf"))
        self._write(folder, labels)
        found = problems(folder)
        self.assertFalse(any("06-scan.pdf" in p for p in found), found)

    def test_binary_md_is_reported(self):
        folder, labels = self._copy()
        (folder / labels[0]["file"]).write_bytes(b"\xff\xfe\x00\x81 not text")
        self._assert_problem(folder, "is not UTF-8")

    def test_file_must_be_a_plain_name(self):
        for bad in ("sub/01.md", "sub\\01.md", "../01-memo-generator.md"):
            with self.subTest(file=bad):
                folder = self._set(lambda label: label.update(file=bad))
                self._assert_problem(folder, "must be a plain file name")


if __name__ == "__main__":
    unittest.main()

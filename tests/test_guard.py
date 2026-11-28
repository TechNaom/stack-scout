"""The search guard (scripts/guard.py): names from the SOW never reach a web search.

A false positive only makes a query more generic, which is safe; a false negative leaks a client's name.
"""
import json
import os
import subprocess
import sys
import unittest

from tests import helpers

import guard

GUARD = helpers.SKILL / "scripts" / "guard.py"
OPTIONS = ["None", "I'll type them"]
SOW = "Halvorsen Freight needs a memo tool. It must run on Azure."


class WordListTest(unittest.TestCase):
    def test_lists_load_lower_case_without_comments(self):
        common, tech = guard.load_words("common-words.txt"), guard.load_words("tech-terms.txt")
        self.assertGreaterEqual(len(common), 1000)
        self.assertGreaterEqual(len(tech), 300)
        for words in (common, tech):
            self.assertFalse(any(w.startswith("#") or w != w.lower() or not w for w in words))
        for w in ["the", "it", "we", "must", "january", "monday"]:
            self.assertIn(w, common)
        for w in ["azure", "aws", "s3", "salesforce", "stripe", "python", "postgres"]:
            self.assertIn(w, tech)


class ExtractTest(unittest.TestCase):
    def setUp(self):
        self.common = guard.load_words("common-words.txt")
        self.tech = guard.load_words("tech-terms.txt")

    def test_client_names_extracted_tech_and_common_words_not(self):
        got = guard.extract_terms(SOW, self.common, self.tech)
        self.assertIn("Halvorsen", got)
        self.assertIn("Halvorsen Freight", got)
        self.assertNotIn("Azure", got)
        self.assertNotIn("It", got)

    def test_acronyms_kept_unless_tech(self):
        got = guard.extract_terms("The HFX team uses AWS and SQL daily.", self.common, self.tech)
        self.assertIn("HFX", got)
        self.assertNotIn("AWS", got)

    def test_runs_do_not_cross_a_sentence_end(self):
        got = guard.extract_terms("We met Quillmere. Brightwater pays.", self.common, self.tech)
        self.assertIn("Quillmere", got)
        self.assertIn("Brightwater", got)
        self.assertNotIn("Quillmere Brightwater", got)

    def test_acronym_that_spells_a_common_word_is_kept(self):
        self.assertIn("all", self.common)
        self.assertNotIn("all", self.tech)
        self.assertIn("ALL", guard.extract_terms("Built for ALL staff.", self.common, self.tech))

    def test_trailing_full_stop_dropped(self):
        got = guard.extract_terms("We work for Quillmere.", self.common, self.tech)
        self.assertIn("Quillmere", got)
        self.assertNotIn("Quillmere.", got)

    def test_extracted_name_blocks_and_generic_query_passes(self):
        extracted = guard.extract_terms(SOW, self.common, self.tech)
        self.assertEqual(guard.check("memo generator azure", set(), extracted, self.tech), [])
        self.assertTrue(guard.check("Halvorsen memo generator", set(), extracted, self.tech))


class LeakTest(unittest.TestCase):
    """Names that slipped past the first version, found by the leak hunt in review."""

    def setUp(self):
        self.common = guard.load_words("common-words.txt")
        self.tech = guard.load_words("tech-terms.txt")

    def blocked(self, sow, query, private=()):
        extracted = guard.extract_terms(sow, self.common, self.tech)
        return guard.check(query, set(private), extracted, self.tech)

    def test_unicode_names(self):
        self.assertTrue(self.blocked("Zoë Müller works here.", "müller memo tool"))
        self.assertTrue(self.blocked("Zoë Müller works here.", "zoë memo tool"))
        self.assertTrue(self.blocked("Østergaard Logistik needs a tool.", "østergaard memo"))

    def test_accents_dropped_in_the_query(self):
        self.assertTrue(self.blocked("Zoë Müller works here.", "muller memo"))
        self.assertTrue(self.blocked("Østergaard Logistik needs a tool.", "ostergaard memo"))
        self.assertTrue(self.blocked("Straße Haulage needs a tool.", "strasse memo"))

    def test_runs_made_only_of_tech_and_common_words_are_not_names(self):
        sow = "We use Google Cloud, Spring Boot and GitHub Actions with a REST API. Node.js runs it."
        for query in ["google cloud storage", "spring boot memo", "github actions ci", "rest api dashboard python", "node.js power bi"]:
            self.assertEqual(self.blocked(sow, query), [], query)
        self.assertEqual(self.blocked("The Data Team reviews Monthly Reports.", "data team monthly reports"), [])

    def test_name_like_tech_words_block_when_capitalised(self):
        # Owner's decision 2026-11-28: tech words that are also common company names are not on the tech list.
        for word in ["shell", "zoom", "chef", "ruby", "jira"]:
            self.assertNotIn(word, self.tech, word)
        self.assertTrue(self.blocked("Our client Shell needs a tool.", "shell memo"))
        self.assertEqual(self.blocked("It runs on Azure.", "azure memo"), [])

    def test_common_word_inside_a_name_blocks_alone(self):
        # Owner's decision 2026-11-28: Brown in "Brown Haulage" is a name; very frequent words like The are not.
        sow = "Brown Haulage and The Halvorsen Group need a tool."
        self.assertTrue(self.blocked(sow, "brown memo"))
        self.assertEqual(self.blocked(sow, "the memo tool"), [])

    def test_name_starting_with_a_digit(self):
        self.assertTrue(self.blocked("The client is 3M.", "3m memo tool"))

    def test_possessive(self):
        self.assertTrue(self.blocked("Halvorsen's team needs a tool.", "halvorsen memo tool"))
        self.assertTrue(self.blocked("Halvorsen’s team needs a tool.", "halvorsen memo tool"))

    def test_hyphen_and_underscore_in_the_query(self):
        for query in ["halvorsen-memo", "halvorsen_memo", "memo-halvorsen"]:
            self.assertTrue(self.blocked("Halvorsen needs a tool.", query), query)

    def test_parts_of_hyphenated_and_dotted_names(self):
        self.assertTrue(self.blocked("Halvorsen-Freight needs a tool.", "halvorsen memo"))
        self.assertTrue(self.blocked("See Halvorsen.com for details.", "halvorsen memo"))

    def test_punctuation_stripped_variants(self):
        self.assertTrue(self.blocked("O'Brien Haulage needs a tool.", "obrien memo"))
        self.assertTrue(self.blocked("Ships for AT&T daily.", "att memo"))

    def test_each_uncommon_part_of_a_private_name_blocks(self):
        self.assertTrue(guard.check("kite memo tool", {"Project Kite"}, set(), self.tech))
        self.assertEqual(guard.check("project memo tool", {"Project Kite"}, set(), self.tech), [])

    def test_tech_names_still_allowed(self):
        self.assertEqual(self.blocked("It runs on Azure and AWS.", "azure aws memo tool"), [])


class CheckTest(unittest.TestCase):
    def test_private_term_blocks_even_when_it_is_a_tech_term(self):
        hits = guard.check("salesforce crm connector", {"Salesforce"}, set(), {"salesforce"})
        self.assertTrue(hits)

    def test_whole_words_only_case_insensitive(self):
        self.assertEqual(guard.check("acmetools for memos", {"Acme"}, set(), set()), [])
        self.assertTrue(guard.check("ACME tools for memos", {"Acme"}, set(), set()))

    def test_regex_characters_in_a_name_are_literal(self):
        self.assertTrue(guard.check("pricing for a.b+c corp", {"A.B+C"}, set(), set()))
        self.assertEqual(guard.check("pricing for axb+c corp", {"A.B+C"}, set(), set()), [])


class AnswersTest(unittest.TestCase):
    def test_typed_names_split_and_trimmed(self):
        got = guard.private_from_answers({"private_names": "Halvorsen; Project Kite, "}, OPTIONS)
        self.assertEqual(got, {"Halvorsen", "Project Kite"})

    def test_option_labels_are_never_terms(self):
        self.assertEqual(guard.private_from_answers({"private_names": "None"}, OPTIONS), set())
        self.assertEqual(guard.private_from_answers({"private_names": "i'll type them"}, OPTIONS), set())
        self.assertEqual(guard.private_from_answers({}, OPTIONS), set())


class CliTest(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.dir = helpers.tmpdir()
        os.environ["STACK_SCOUT_DIR"] = str(self.dir)
        os.environ["STACK_SCOUT_NOW"] = "2026-11-27T10:00:00Z"
        os.environ["STACK_SCOUT_NO_GH"] = "1"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def run_guard(self, *args):
        proc = subprocess.run([sys.executable, str(GUARD), *args], capture_output=True, text=True,
                              encoding="utf-8", env=dict(os.environ), timeout=60)
        self.assertNotIn("Traceback", proc.stderr)
        return proc.returncode, json.loads(proc.stdout), proc.stdout + proc.stderr

    def test_terms_then_check_round_trip_without_printing_the_sow(self):
        sow = self.dir / "sow.txt"
        sow.write_text(SOW + " Contact Brightwater Analytics.", encoding="utf-8")
        private = self.dir / "private.txt"
        private.write_text("Project Kite\n", encoding="utf-8")
        code, out, raw = self.run_guard("terms", "--sow", str(sow), "--private-terms", str(private))
        self.assertEqual(code, 0)
        self.assertEqual(out["ok"], True)
        self.assertEqual(out["private"], 1)
        self.assertGreaterEqual(out["extracted"], 2)
        for secret in ["Halvorsen", "Brightwater", "Kite", "memo tool"]:
            self.assertNotIn(secret, raw)
        terms = json.loads((self.dir / "terms.json").read_text(encoding="utf-8"))
        self.assertIn("Project Kite", terms["private"])
        self.assertIn("Halvorsen Freight", terms["extracted"])

        self.assertEqual(self.run_guard("check", "memo generator azure")[:2], (0, {"ok": True}))
        code, out, _ = self.run_guard("check", "project kite memo tool")
        self.assertEqual(code, 2)
        self.assertEqual(out["ok"], False)
        self.assertTrue(out["hits"])

    def test_answers_file_adds_typed_names(self):
        sow = self.dir / "sow.txt"
        sow.write_text("We need a memo tool.", encoding="utf-8")
        answers = self.dir / "answers.json"
        answers.write_text(json.dumps({"private_names": "Halvorsen; None"}), encoding="utf-8")
        code, out, _ = self.run_guard("terms", "--sow", str(sow), "--answers", str(answers))
        self.assertEqual((code, out["private"]), (0, 1))
        self.assertEqual(self.run_guard("check", "halvorsen")[0], 2)

    def test_check_before_terms_is_refused(self):
        code, out, _ = self.run_guard("check", "anything")
        self.assertEqual(code, 2)
        self.assertEqual(out, {"ok": False, "error": "run guard.py terms first"})


if __name__ == "__main__":
    unittest.main()

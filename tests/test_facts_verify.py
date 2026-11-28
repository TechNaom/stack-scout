"""facts.py verify and to-verify: GitHub facts in batches, the REST-only mode, the bot rule, rate limits."""
import json
import os
import subprocess
import sys
import unittest

from tests import helpers

import common
import facts
from tests.mock_api import MockAPI

FACTS = helpers.SKILL / "scripts" / "facts.py"
NOW = "2026-11-27T10:00:00Z"


def commit(date, login=None, name="someone"):
    return {"committedDate": date, "author": {"name": name, "user": {"login": login} if login else None}}


def repo_node(name, stars=10, licence="MIT", release="2026-10-01T12:00:00Z", history=None):
    owner, repo = name.split("/")
    return {
        "url": f"https://github.com/{owner}/{repo}", "stargazerCount": stars, "isArchived": False,
        "licenseInfo": {"spdxId": licence} if licence else None,
        "latestRelease": {"publishedAt": release} if release else None,
        "primaryLanguage": {"name": "Python"},
        "defaultBranchRef": {"target": {"history": {"nodes": history if history is not None else [
            commit("2026-11-20T08:00:00Z", login="alice")]}}},
    }


def graphql(names, cost=1, **per_repo):
    data = {f"r{i}": repo_node(n, **per_repo.get(n, {})) for i, n in enumerate(names)}
    data["rateLimit"] = {"cost": cost, "remaining": 4990, "resetAt": "2026-11-27T11:00:00Z"}
    return {"data": data}


class FactsTest(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.dir = helpers.tmpdir()
        os.environ.update({"STACK_SCOUT_DIR": str(self.dir), "STACK_SCOUT_NOW": NOW, "STACK_SCOUT_NO_SLEEP": "1",
                           "STACK_SCOUT_NO_GH": "1", "GITHUB_TOKEN": "test-token"})
        self.api = MockAPI().__enter__()
        os.environ["STACK_SCOUT_GITHUB_API"] = self.api.url

    def tearDown(self):
        self.api.__exit__(None, None, None)
        os.environ.clear()
        os.environ.update(self._env)

    def run_facts(self, *args):
        proc = subprocess.run([sys.executable, str(FACTS), *args], capture_output=True, text=True,
                              encoding="utf-8", env=dict(os.environ), timeout=60)
        self.assertNotIn("Traceback", proc.stderr)
        return proc.returncode, json.loads(proc.stdout)

    def saved(self):
        return {(f["subject"], f["field"]): f for f in common.load_facts(common.facts_path())}

    def graphql_calls(self):
        return [r for r in self.api.requests if r[0] == "POST" and r[1].startswith("/graphql")]


class GraphQLTest(FactsTest):
    def test_two_repositories_in_one_request_with_points_metered(self):
        self.api.route("POST", "/graphql", [(200, {}, graphql(["a/one", "b/two"], cost=3))])
        code, out = self.run_facts("verify", "a/one", "b/two")
        self.assertEqual((code, out["ok"], out["mode"], out["partial"]), (0, True, "graphql", False))
        self.assertEqual(sorted(out["checked"]), ["a/one", "b/two"])
        self.assertEqual(len(self.graphql_calls()), 1)
        self.assertEqual(self.graphql_calls()[0][2].get("Authorization"), "Bearer test-token")
        facts_ = self.saved()
        self.assertEqual(facts_[("github:a/one", "stars")]["value"], 10)
        self.assertEqual(facts_[("github:a/one", "exists")]["value"], True)
        self.assertEqual(facts_[("github:a/one", "licence")]["value"], "MIT")
        self.assertEqual(facts_[("github:a/one", "latest_release")]["value"], "2026-10-01")
        self.assertEqual(facts_[("github:a/one", "last_activity")]["value"], "2026-11-20")
        self.assertEqual(facts_[("github:a/one", "primary_language")]["value"], "Python")
        self.assertEqual(facts_[("github:a/one", "stars")]["source"], "https://github.com/a/one")
        run = json.loads((self.dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(run["github_points"], 3)

    def test_twenty_one_repositories_make_two_requests(self):
        names = [f"o/r{i}" for i in range(21)]
        self.api.route("POST", "/graphql", [(200, {}, graphql(names[:20])), (200, {}, graphql(names[20:]))])
        code, out = self.run_facts("verify", *names)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.graphql_calls()), 2)
        self.assertEqual(len(out["checked"]), 21)

    def test_bot_only_history_needs_checking_and_a_human_after_bots_counts(self):
        bots = [commit("2026-11-25T08:00:00Z", login="dependabot[bot]"), commit("2026-11-24T08:00:00Z", name="renovate")]
        human = [commit("2026-11-26T08:00:00Z", login="renovate"), commit("2026-11-23T08:00:00Z", login="carol")] + bots
        self.api.route("POST", "/graphql", [(200, {}, graphql(["a/bots", "a/human"], **{
            "a/bots": {"history": bots}, "a/human": {"history": human}}))])
        self.assertEqual(self.run_facts("verify", "a/bots", "a/human")[0], 0)
        facts_ = self.saved()
        self.assertIsNone(facts_[("github:a/bots", "last_activity")]["value"])
        self.assertEqual(facts_[("github:a/bots", "last_activity")]["to_verify"],
                         "only bot activity in the last 100 commits")
        self.assertEqual(facts_[("github:a/human", "last_activity")]["value"], "2026-11-23")

    def test_not_found_alias_is_missing_with_exists_false(self):
        body = graphql(["a/one"])
        body["data"]["r1"] = None
        body["errors"] = [{"type": "NOT_FOUND", "path": ["r1"], "message": "Could not resolve"}]
        self.api.route("POST", "/graphql", [(200, {}, body)])
        code, out = self.run_facts("verify", "a/one", "a/gone")
        self.assertEqual(code, 0)
        self.assertEqual(out["missing"], ["a/gone"])
        facts_ = self.saved()
        self.assertEqual(facts_[("github:a/gone", "exists")]["value"], False)
        self.assertNotIn(("github:a/gone", "stars"), facts_)
        self.assertEqual(facts_[("github:a/one", "exists")]["value"], True)

    def test_noassertion_licence_is_null_with_to_verify(self):
        self.api.route("POST", "/graphql", [(200, {}, graphql(["a/one", "a/two"], **{
            "a/one": {"licence": "NOASSERTION"}, "a/two": {"licence": None, "release": None}}))])
        self.run_facts("verify", "a/one", "a/two")
        facts_ = self.saved()
        for name in ["a/one", "a/two"]:
            lic = facts_[(f"github:{name}", "licence")]
            self.assertIsNone(lic["value"])
            self.assertEqual(lic["to_verify"], "no licence GitHub can identify")
        release = facts_[("github:a/two", "latest_release")]
        self.assertIsNone(release["value"])
        self.assertNotIn("to_verify", release)  # "no releases" is a fact

    def test_rate_limited_second_batch_keeps_the_first(self):
        names = [f"o/r{i}" for i in range(21)]
        self.api.route("POST", "/graphql", [(200, {}, graphql(names[:20])), (429, {}, None)])
        code, out = self.run_facts("verify", *names)
        self.assertEqual((code, out["partial"]), (3, True))
        self.assertEqual(out["unchecked"], ["o/r20"])
        self.assertEqual(len(out["checked"]), 20)
        self.assertIn(("github:o/r19", "stars"), self.saved())
        run = json.loads((self.dir / "run.json").read_text(encoding="utf-8"))
        self.assertTrue(run["partial"])

    def test_rate_limit_as_http_200_errors(self):
        self.api.route("POST", "/graphql", [(200, {}, {"errors": [{"type": "RATE_LIMITED", "message": "slow down"}]})])
        code, out = self.run_facts("verify", "a/one")
        self.assertEqual((code, out["partial"], out["unchecked"]), (3, True, ["a/one"]))

    def test_empty_repository_has_no_commits(self):
        body = graphql(["a/empty"])
        body["data"]["r0"]["defaultBranchRef"] = None
        self.api.route("POST", "/graphql", [(200, {}, body)])
        self.assertEqual(self.run_facts("verify", "a/empty")[0], 0)
        item = self.saved()[("github:a/empty", "last_activity")]
        self.assertEqual((item["value"], item["to_verify"]), (None, "no commits on the default branch"))

    def test_hidden_alias_is_unchecked_and_the_rest_is_kept(self):
        body = graphql(["a/one"])
        body["data"]["r1"] = None
        body["errors"] = [{"type": "FORBIDDEN", "path": ["r1"], "message": "SAML enforcement"}]
        self.api.route("POST", "/graphql", [(200, {}, body)])
        code, out = self.run_facts("verify", "a/one", "corp/secret")
        self.assertEqual((code, out["partial"], out["unchecked"], out["checked"]), (3, True, ["corp/secret"], ["a/one"]))
        self.assertIn(("github:a/one", "stars"), self.saved())
        self.assertNotIn(("github:corp/secret", "exists"), self.saved())

    def test_server_error_on_the_second_batch_keeps_the_first(self):
        names = [f"o/r{i}" for i in range(21)]
        self.api.route("POST", "/graphql", [(200, {}, graphql(names[:20])), (502, {}, {"message": "bad gateway"})])
        code, out = self.run_facts("verify", *names)
        self.assertEqual((code, out["ok"]), (2, False))
        self.assertIn(("github:o/r19", "stars"), self.saved())

    def test_meter_counts_one_script_call_and_the_points_of_a_partial_run(self):
        names = [f"o/r{i}" for i in range(21)]
        self.api.route("POST", "/graphql", [(200, {}, graphql(names[:20], cost=4)), (429, {}, None)])
        self.assertEqual(self.run_facts("verify", *names)[0], 3)
        run = json.loads((self.dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual((run["script_calls"], run["github_points"], run["partial"]), (1, 4, True))
        self.assertEqual(len(self.graphql_calls()), 5)  # the 429 was retried 3 times before giving up

    def test_repeated_names_are_checked_once(self):
        self.api.route("POST", "/graphql", [(200, {}, graphql(["a/one"]))])
        code, out = self.run_facts("verify", "a/one", "a/one")
        self.assertEqual((code, out["checked"]), (0, ["a/one"]))

    def test_verify_checks_names_itself(self):
        with self.assertRaisesRegex(common.CoreError, "^not owner/repo: "):
            facts.verify(['a/b") { id } x: repository(owner: "c'])
        self.assertEqual(self.graphql_calls(), [])


class RestTest(FactsTest):
    def test_no_token_uses_rest_only(self):
        os.environ["GITHUB_TOKEN"] = ""
        self.api.route("GET", "/repos/a/one", [(200, {}, {
            "html_url": "https://github.com/a/one", "stargazers_count": 7, "archived": True,
            "license": {"spdx_id": "Apache-2.0"}})])
        self.api.route("GET", "/repos/a/one/commits", [(200, {}, [
            {"commit": {"author": {"name": "dependabot", "date": "2026-11-25T08:00:00Z"}}, "author": {"login": "dependabot[bot]"}},
            {"commit": {"author": {"name": "dan", "date": "2026-11-21T08:00:00Z"}}, "author": {"login": "dan"}}])])
        self.api.route("GET", "/repos/a/gone", [(404, {}, {"message": "Not Found"})])
        code, out = self.run_facts("verify", "a/one", "a/gone")
        self.assertEqual((code, out["mode"]), (0, "rest"))
        self.assertIn("note", out)
        self.assertEqual(self.graphql_calls(), [])
        self.assertTrue(any(r[1] == "/repos/a/one/commits?per_page=100" for r in self.api.requests))
        self.assertNotIn("Authorization", self.api.requests[0][2])
        facts_ = self.saved()
        self.assertEqual(facts_[("github:a/one", "stars")]["value"], 7)
        self.assertEqual(facts_[("github:a/one", "archived")]["value"], True)
        self.assertEqual(facts_[("github:a/one", "licence")]["value"], "Apache-2.0")
        self.assertEqual(facts_[("github:a/one", "last_activity")]["value"], "2026-11-21")
        for field in ["latest_release", "primary_language"]:
            self.assertEqual(facts_[("github:a/one", field)]["to_verify"], "needs a GitHub sign-in: run gh auth login")
        self.assertEqual(facts_[("github:a/gone", "exists")]["value"], False)
        self.assertEqual(out["missing"], ["a/gone"])

    def test_empty_repository_in_rest_mode(self):
        os.environ["GITHUB_TOKEN"] = ""
        self.api.route("GET", "/repos/a/one", [(200, {}, {"stargazers_count": 1, "archived": False, "license": None})])
        self.api.route("GET", "/repos/a/one/commits", [(409, {}, {"message": "Git Repository is empty."})])
        self.api.route("GET", "/repos/a/two", [(200, {}, {"stargazers_count": 2, "archived": False, "license": None})])
        self.api.route("GET", "/repos/a/two/commits", [(200, {}, [])])
        code, out = self.run_facts("verify", "a/one", "a/two")
        self.assertEqual((code, out["checked"]), (0, ["a/one", "a/two"]))
        item = self.saved()[("github:a/one", "last_activity")]
        self.assertEqual((item["value"], item["to_verify"]), (None, "no commits on the default branch"))

    def test_rest_rate_limit_lists_the_rest_as_unchecked(self):
        os.environ["GITHUB_TOKEN"] = ""
        self.api.route("GET", "/repos/a/one", [(200, {}, {"stargazers_count": 1, "archived": False, "license": None})])
        self.api.route("GET", "/repos/a/one/commits", [(200, {}, [])])
        self.api.route("GET", "/repos/a/two", [(429, {}, None)])
        code, out = self.run_facts("verify", "a/one", "a/two", "a/three")
        self.assertEqual((code, out["checked"], out["unchecked"]), (3, ["a/one"], ["a/two", "a/three"]))
        self.assertIn(("github:a/one", "stars"), self.saved())


class CliTest(FactsTest):
    def test_to_verify_writes_a_null_fact(self):
        code, out = self.run_facts("to-verify", "price:x", "price", "not checked", "--source", "https://example.com/pricing")
        self.assertEqual((code, out["ok"]), (0, True))
        item = self.saved()[("price:x", "price")]
        self.assertIsNone(item["value"])
        self.assertEqual((item["to_verify"], item["source"]), ("not checked", "https://example.com/pricing"))

    def test_to_verify_needs_https(self):
        code, out = self.run_facts("to-verify", "price:x", "price", "not checked", "--source", "http://example.com")
        self.assertEqual((code, out["ok"]), (2, False))
        self.assertEqual(out["error"], "--source must start with https://")

    def test_malformed_repository_name(self):
        for bad in ["noslash", "a/b/c", "../etc", "a /b"]:
            code, out = self.run_facts("verify", bad)
            self.assertEqual(code, 2, bad)
            self.assertEqual(out, {"ok": False, "error": f"not owner/repo: {bad}"})


class BotTest(unittest.TestCase):
    def test_is_bot(self):
        self.assertTrue(facts.is_bot("dependabot[bot]", None))
        self.assertTrue(facts.is_bot("some-app[bot]", "x"))
        self.assertTrue(facts.is_bot(None, "Renovate"))
        self.assertTrue(facts.is_bot("github-actions", None))
        self.assertFalse(facts.is_bot("alice", "Alice"))
        self.assertFalse(facts.is_bot(None, None))


if __name__ == "__main__":
    unittest.main()

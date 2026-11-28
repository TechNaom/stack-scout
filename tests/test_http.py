"""HTTP client (common.http_json) against the local mock API: back-off, rate limits, no token in errors."""
import os
import unittest

# The helpers module adjusts sys.path so that the scripts can be imported.
from tests import helpers  # noqa: F401
import common
from tests.mock_api import MockAPI


class TestHTTP(unittest.TestCase):
    def setUp(self):
        # Ensure back‑off sleeps are disabled for the tests.
        self._original_no_sleep = os.environ.get("STACK_SCOUT_NO_SLEEP")
        os.environ["STACK_SCOUT_NO_SLEEP"] = "1"

    def tearDown(self):
        # Restore the original environment variable.
        if self._original_no_sleep is None:
            os.environ.pop("STACK_SCOUT_NO_SLEEP", None)
        else:
            os.environ["STACK_SCOUT_NO_SLEEP"] = self._original_no_sleep

    def test_200_returns_body(self):
        with MockAPI() as api:
            api.route("GET", "/x", [(200, {}, {"ok": True})])
            status, data = common.http_json("GET", f"{api.url}/x")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True})

    def test_404_returns_status_without_raising(self):
        with MockAPI() as api:
            api.route("GET", "/x", [(404, {}, {"message": "Not Found"})])
            status, data = common.http_json("GET", f"{api.url}/x")
        self.assertEqual(status, 404)
        self.assertEqual(data, {"message": "Not Found"})

    def test_one_429_then_200_succeeds_and_two_requests_made(self):
        with MockAPI() as api:
            api.route(
                "GET",
                "/x",
                [
                    (429, {"Retry-After": "1"}, None),
                    (200, {}, {"ok": True}),
                ],
            )
            status, data = common.http_json("GET", f"{api.url}/x")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True})
        self.assertEqual(len(api.requests), 2)

    def test_429_with_long_retry_after_raises_rate_limited_after_one_request(self):
        with MockAPI() as api:
            api.route("GET", "/x", [(429, {"Retry-After": "3600"}, None)])
            with self.assertRaises(common.RateLimited) as ctx:
                common.http_json("GET", f"{api.url}/x")
        exc = ctx.exception
        self.assertEqual(exc.status, 429)
        self.assertEqual(len(api.requests), 1)

    def test_multiple_403s_with_rate_limit_remaining_zero_raises_rate_limited(self):
        with MockAPI() as api:
            # Four identical 403 responses; the client will retry 3 times + the initial attempt.
            api.route(
                "GET",
                "/x",
                [
                    (403, {"x-ratelimit-remaining": "0"}, None),
                    (403, {"x-ratelimit-remaining": "0"}, None),
                    (403, {"x-ratelimit-remaining": "0"}, None),
                    (403, {"x-ratelimit-remaining": "0"}, None),
                ],
            )
            with self.assertRaises(common.RateLimited) as ctx:
                common.http_json("GET", f"{api.url}/x", retries=3)
        exc = ctx.exception
        self.assertEqual(exc.status, 403)
        self.assertEqual(len(api.requests), 4)

    def test_token_sent_in_authorization_header_and_not_exposed_in_error(self):
        token = "ghp_" + "x" * 36
        with MockAPI() as api:
            api.route("GET", "/x", [(500, {}, {"message": f"bad credentials {token}"})])
            with self.assertRaises(RuntimeError) as ctx:
                common.http_json("GET", f"{api.url}/x", token=token)
        # The token must not appear in the exception message.
        self.assertNotIn(token, str(ctx.exception))
        self.assertIn("***", str(ctx.exception))
        # Verify the Authorization header was correctly set.
        self.assertTrue(api.requests)  # at least one request recorded
        req_headers = api.requests[0][2]
        self.assertIn("Authorization", req_headers)
        self.assertEqual(req_headers["Authorization"], f"Bearer {token}")

    def test_post_sends_json_body_and_user_agent_header(self):
        payload = {"name": "test", "value": 123}
        with MockAPI() as api:
            api.route("POST", "/x", [(200, {}, {"ok": True})])
            status, data = common.http_json("POST", f"{api.url}/x", body=payload)
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True})
        # Verify request details.
        self.assertTrue(api.requests)
        method, path, headers, body = api.requests[0]
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/x")
        # Body should be JSON‑decoded (the mock parses it).
        self.assertEqual(body, payload)
        # User‑Agent header must be present.
        self.assertIn("User-Agent", headers)
        self.assertEqual(headers["User-Agent"], "stack-scout")


if __name__ == "__main__":
    unittest.main()

"""HTTP client (common.http_json) against the local mock API: back-off, rate limits, no token in errors."""
import os
import time
import unittest
from unittest import mock

# The helpers module adjusts sys.path so that the scripts can be imported.
from tests import helpers  # noqa: F401
import common
from tests.mock_api import MockAPI


class TestHTTP(unittest.TestCase):
    def setUp(self):
        # Ensure back-off sleeps are disabled for the tests.
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
        # Body should be JSON-decoded (the mock parses it).
        self.assertEqual(body, payload)
        # User-Agent header must be present.
        self.assertIn("User-Agent", headers)
        self.assertEqual(headers["User-Agent"], "stack-scout")

    def test_403_without_rate_limit_header_is_an_error_after_one_request(self):
        with MockAPI() as api:
            api.route("GET", "/x", [(403, {}, {"message": "Forbidden"})])
            with self.assertRaises(RuntimeError):
                common.http_json("GET", f"{api.url}/x")
        self.assertEqual(len(api.requests), 1)

    def test_far_ratelimit_reset_raises_at_once_with_reset_at(self):
        reset = int(time.time()) + 3600
        with MockAPI() as api:
            api.route("GET", "/x", [(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(reset)}, None)])
            with self.assertRaises(common.RateLimited) as ctx:
                common.http_json("GET", f"{api.url}/x")
        self.assertEqual(ctx.exception.reset_at, reset)
        self.assertEqual(len(api.requests), 1)

    def test_default_back_off_is_2_4_8_seconds(self):
        os.environ.pop("STACK_SCOUT_NO_SLEEP", None)
        with MockAPI() as api, mock.patch.object(common.time, "sleep") as sleep:
            api.route("GET", "/x", [(429, {}, None)])
            with self.assertRaises(common.RateLimited):
                common.http_json("GET", f"{api.url}/x", retries=3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4, 8])

    def test_bad_retry_after_values_fall_back_without_crashing(self):
        os.environ.pop("STACK_SCOUT_NO_SLEEP", None)
        for value in ("-5", "nan", "Wed, 21 Oct 2015 07:28:00 GMT"):
            with self.subTest(value=value), MockAPI() as api, mock.patch.object(common.time, "sleep") as sleep:
                api.route("GET", "/x", [(429, {"Retry-After": value}, None), (200, {}, {"ok": True})])
                self.assertEqual(common.http_json("GET", f"{api.url}/x"), (200, {"ok": True}))
                waits = [c.args[0] for c in sleep.call_args_list]
                self.assertTrue(all(w == w and 0 <= w <= 60 for w in waits), waits)  # w == w is False for nan

    def test_closed_port_raises_runtime_error_without_token(self):
        token = "ghp_" + "y" * 36
        with MockAPI() as api:
            url = api.url
        with self.assertRaises(RuntimeError) as ctx:
            common.http_json("GET", f"{url}/x?t={token}", token=token)
        self.assertNotIn(token, str(ctx.exception))

    def test_non_utf8_body_returns_none(self):
        with MockAPI() as api:
            api.route("GET", "/x", [(200, {}, bytes([0xFF, 0xFE]) + b" not utf-8")])
            self.assertEqual(common.http_json("GET", f"{api.url}/x"), (200, None))


if __name__ == "__main__":
    unittest.main()

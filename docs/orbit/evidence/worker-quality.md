# Free-worker quality log

Each row is one draft from a free model (via the free-router), reviewed by the supervisor before anything was
written to the repo. Only public, non-sensitive work goes to free workers.

| Date | Task | Tier / model | Time | What it drafted | Review result | Fixes the supervisor made |
|---|---|---|---|---|---|---|
| 2026-11-28 | T5 | fast / groq gpt-oss-120b | 19.1 s | tests/mock_api.py (162 lines) | usable, 2 real bugs | next response picked outside the lock (race between concurrent requests); stored header dicts mutated (Content-Length leaked into reused responses); rewrote it at about half the size |
| 2026-11-28 | T5 | fast / groq gpt-oss-120b | 6.7 s | tests/test_http.py (7 tests) | good, 3 weak tests | 404 test asserted nothing; over-specified `reset_at is None`; the token test could not fail (token never in the 500 text), fixed by echoing the token in the mock body and asserting `***` |
| 2026-11-28 | T5 | heavy_code / nemotron-3-ultra (OpenRouter free, first in the chain) | 31.4 s | `http_json`, `RateLimited`, API base functions | good, logic correct | imports moved to the top; `Retry-After: 0` and a malformed Retry-After now handled (supervisor's own edit, then simplified); both mutants (no redaction, no 60 s cap) killed by the tests |

Claude work saved on T5: roughly the drafting of 3 files (about 350 lines); review and fixes still took supervisor
time. Next: more rows before any quality score is claimed.

After review, the combined Sonnet check still found 2 code edge cases (negative/nan Retry-After; non-UTF-8 body) in
the Nemotron draft and 4 untested card behaviours in the gpt-oss tests. Both drafts passed every test they came
with, so "tests pass" was not enough evidence of quality for worker output either.

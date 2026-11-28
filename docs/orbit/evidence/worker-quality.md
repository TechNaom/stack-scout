# Free-worker quality log

Each row is one draft from a free model (via the free-router), reviewed by the supervisor before anything was
written to the repo. Only public, non-sensitive work goes to free workers.

| Date | Task | Tier / model | Time | What it drafted | Review result | Fixes the supervisor made |
|---|---|---|---|---|---|---|
| 2026-11-28 | T5 | fast / groq gpt-oss-120b | 19.1 s | tests/mock_api.py (162 lines) | usable, 2 real bugs | next response picked outside the lock (race between concurrent requests); stored header dicts mutated (Content-Length leaked into reused responses); rewrote it at about half the size |
| 2026-11-28 | T5 | fast / groq gpt-oss-120b | 6.7 s | tests/test_http.py (7 tests) | good, 3 weak tests | 404 test asserted nothing; over-specified `reset_at is None`; the token test could not fail (token never in the 500 text), fixed by echoing the token in the mock body and asserting `***` |
| 2026-11-28 | T5 | heavy_code / nemotron-3-ultra (OpenRouter free, first in the chain) | 31.4 s | `http_json`, `RateLimited`, API base functions | good, logic correct | imports moved to the top; `Retry-After: 0` and a malformed Retry-After now handled (supervisor's own edit, then simplified); both mutants (no redaction, no 60 s cap) killed by the tests |
| 2026-11-28 | T6 | fast / groq gpt-oss-120b | 11.5 s | tech-terms list (612 unique) | usable | missed s3, ec2, lambda although the prompt named them; one junk entry (hug) |
| 2026-11-28 | T6 | context / gemini-3.1-flash-lite (after gemini-3.5-flash 503 and nemotron-lightning empty) | 70.6 s | common-words list | not usable as asked | 1,272 words, not frequency-ranked (alphabetical verbs past 1,000) |
| 2026-11-28 | T6 | fast / groq gpt-oss-120b | 11.7 s | frequency-ranked list | partial | stopped at 846 lines (output cap); only 366 unique words |
| 2026-11-28 | T6 | fast / groq qwen3.8-27b (fallback) | 15.4 s | ranks 847-1100 | failed | looped: the same 9 words repeated for 250 lines |
| 2026-11-28 | T6 | fast / groq gpt-oss-120b | 44.7 s | "Ogden's Basic English 850" | not as labelled | 1,103 words, 7 of the 100 core words missing; used only as extra common words, not credited to Ogden |
| 2026-11-28 | T6 | heavy_code (all three) | 225 s | guard.py | failed | OpenRouter empty reply, NVIDIA timeout, Gemini Pro 429; the supervisor wrote it |

Claude work saved on T5: roughly the drafting of 3 files (about 350 lines); review and fixes still took supervisor
time. Next: more rows before any quality score is claimed.

After review, the combined Sonnet check still found 2 code edge cases (negative/nan Retry-After; non-UTF-8 body) in
the Nemotron draft and 4 untested card behaviours in the gpt-oss tests. Both drafts passed every test they came
with, so "tests pass" was not enough evidence of quality for worker output either.

## Tally so far (9 drafts, 2026-11-28)
- Usable after fixes: 4 (mock server, tests, http client, tech list). Good as is: 0.
- Partial or not as asked: 3 (word lists). Failed outright: 2 (a looping fallback model; every heavy_code
  provider down for one request).
- Strong at: boilerplate and well-specified code with tests to check it. Weak at: long exact lists (cut-offs,
  loops, padding), following an explicit "include these" list, and availability (rate limits, empty replies).
- Every usable draft needed review fixes; three more problems were found only by the Sonnet check.


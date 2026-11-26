# ADR 0006: The user's own model reasons; code owns every fact, every query and the final check

Date: 2026-11-27. Status: proposed

## Context
- **N2:** no invented projects, licences or numbers.
- **N3:** confidential SOWs must not leak into searches.
- **R16:** the picks must fit together.
- **N1:** Rs 0 to run, within the user's Claude quota.

## Options

| Option | Fit | Cost | Effort | Lock-in | On failure |
|---|---|---|---|---|---|
| A. The model in the user's Claude Code session does the reasoning: reading the SOW, finding the open points, naming capabilities, choosing among verified candidates, writing reasons. Code does the rest: `guard.py` checks every search query, `facts.py`, `osv.py` and `licence.py` fetch facts, and `validate.py` checks the finished `stack.json` | No API key and no cost (N1); facts can't be invented because `validate.py` rejects any project, number or licence not in this run's facts file | Rs 0 | Medium | Claude Code | `validate.py` fails: the skill fixes the stack or marks the item "to verify"; it never ships an unvalidated stack |
| B. Our own API calls to a chosen model | Same behaviour on every surface | The user pays per call, with their own key | Medium | A provider | Key missing: no run |

## Decision
Option A.
- **The model may never:** state a fact about a project or a price that is not in the facts file; send a search
  query that `guard.py` has not passed; leave a capability empty without the "build it yourself" or "use a managed
  service" outcome (R7).
- **`guard.py`** extracts the SOW's protected terms: proper nouns, names the user gave in the interview, and a
  `--private-terms` list. It blocks any query that contains them, so queries are built from generic capability
  names only.
- **`validate.py`** checks the finished stack:
  - every repository in `stack.json` is in the facts file, with matching numbers;
  - every managed service has a pricing link with a date, or "to verify";
  - the compatibility rules hold (R16): one main language and runtime per layer, libraries in that layer's
    ecosystem, no clashing major versions declared in their manifests.

## Why
The user's own model gives the interview and reasoning for free, and code makes the hard rules enforceable instead of
hoped-for. Option B returns for the CLI (R13).

## Revisit when
The CLI is built: it reuses the same scripts with an API model.

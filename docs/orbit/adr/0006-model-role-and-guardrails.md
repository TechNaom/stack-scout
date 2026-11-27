# ADR 0006: The user's own model reasons; code owns every fact, every query and the final check

Date: 2026-11-27. Status: accepted

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
  names only. A list of technology words (`data/tech-terms.txt`, built from GitHub's topic names) is never treated
  as private, so "must run on Azure" can still search for Azure tools. **Names the user gives in the interview
  or in `--private-terms` always beat the allowlist:** GitHub topics include company names (stripe, shopify,
  salesforce), so if the client is Salesforce, "Salesforce" is blocked even though it is a topic. An eval plants a
  client name that is also a GitHub topic.
- **Searches the scripts don't make:** the model's own web searches and page lookups (finding a pricing page,
  extra candidates) don't go through `facts.py`. The skill runs `guard.py check "<query>"` before each of them.
  **This can't be enforced in code.** Like the 200-call cap, an eval checks the session transcript: no web query
  contains a planted private term.
- **`validate.py`** checks the finished stack:
  - every repository and service in `stack.json` is in the facts file. `stack.json` holds only references
    (`subject`), never copied values; `stack.md` shows facts by rendering them from the facts file, so values can't
    drift and are not compared;
  - the model's own prose fields (`reason`, `why_not`, `risks`) contain no **fact-shaped text**: star or download
    counts ("40k", "12,000 stars"), percentages, prices with a currency, and dates. Digits inside technology
    words and version numbers are allowed (Python 3, OAuth 2.0, HTTP/2, S3, EC2, ISO 27001, Postgres 16). Licences
    are matched as SPDX ids and full licence phrases ("Apache-2.0", "Apache License", "MIT License", "GPL-3.0"),
    never a bare word, so "Apache Kafka" passes. A fact written in prose ("40k stars, MIT License") is rejected,
    so facts appear only as rendered values;
  - every managed service has a pricing link with a date, or "to verify";
  - the compatibility rules hold (R16): one main language and runtime per layer, libraries in that layer's
    ecosystem, no clashing major versions declared in their manifests.

## Why
The user's own model gives the interview and reasoning for free, and code makes the hard rules enforceable instead of
hoped-for. Option B returns for the CLI (R13).

## Revisit when
The CLI is built: it reuses the same scripts with an API model.

# ADR 0002: GitHub facts come from batched GraphQL calls with the user's own login

Date: 2026-11-27. Status: accepted

## Context
R5 (check each candidate live: exists, stars, licence, last push, archived, latest release, contributors), N1 (about
200 tool calls a run), N6 (respect rate limits). Facts checked 2026-11-27 ([REST limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api),
[GraphQL limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api)):
- Unauthenticated REST: 60 requests an hour.
- GraphQL: about 5,000 points an hour for a signed-in user; at most 2,000 points a minute.
- Search has its own smaller limit, shown by `/rate_limit`.

## Options

| Option | Fit | Cost | Effort | Lock-in | On failure |
|---|---|---|---|---|---|
| A. `scripts/facts.py`: one GraphQL query fetches up to about 20 repositories at once (stars, licence SPDX, isArchived, latest release, primary language, default-branch manifest files, and the **default branch's recent commits with their authors**: the last commit by a non-bot author counts as "last activity", because `pushedAt` counts pushes to any branch, including bots such as Dependabot; if the last 100 commits on the default branch are all by bots, the result is "only bot activity in the last 100 commits: to verify", never alive and never silently dead); contributor counts by REST, only for finalists. Token from `GITHUB_TOKEN` or `gh auth token`. **GraphQL always needs a token.** Without one, a REST-only mode (60 requests an hour, searches about 10 a minute): basic facts for the finalists only (exists, stars, licence, archived, last commit), everything else "to verify", and a prompt to run `gh auth login` | 24 candidates in 2 calls; well within limits | Rs 0 | Low | GitHub | 403 or 429: back off and retry with limits, then mark the unchecked facts "to verify" |
| B. The official GitHub MCP server | Rich | Rs 0 | Users must install and sign in to another server | Low | Server missing: no facts |
| C. One REST call per fact | Simple | Rs 0 | Low | GitHub | About 100+ calls a run, and exhausts unauthenticated limits at once |

## Decision
Option A. Every fact is saved to `.stack-scout/facts-<date>.json` with its source and time, so a run never asks twice
and `validate.py` (ADR 0006) can check every claim against it.

## Why
Batching keeps a run to a few calls (the PRD's 200-call cap is for the whole session); the user's own `gh` login is
the easiest token to get. We give up working well with no token at all.

## Revisit when
GitHub changes GraphQL limits, or users mostly lack `gh`.

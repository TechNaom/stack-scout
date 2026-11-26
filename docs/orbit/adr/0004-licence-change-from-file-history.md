# ADR 0004: A recent licence change is found from the licence file's own history

Date: 2026-11-27. Status: proposed

## Context
R6 flags projects whose licence changed to a source-available one in the last 24 months. GitHub's API returns only
the **current** licence (SPDX id, or "NOASSERTION").

## Options

| Option | Fit | Cost | Effort | Lock-in | On failure |
|---|---|---|---|---|---|
| A. For each finalist, get the licence file's real path first (REST `/repos/{owner}/{repo}/license`: it may be
LICENSE.md, LICENCE, COPYING and so on), then list commits touching that path in the last 24 months
(`commits?path=<path>&since=`, which also shows renames: an earlier name found in a rename is searched too); if any, fetch the file as it was just before the window and compare the licence family (permissive, copyleft, source-available) with today's | Catches the Redis, Terraform and Elastic kind of change; 1 call per finalist, 2 only when the file changed | Rs 0 | Medium: licence-family detection by known phrases | GitHub | Unclear text: "licence changed in <month>, to verify" |
| B. A hand-kept list of known relicensed projects | Easy | Rs 0 | High: always out of date | n/a | Misses every new case |

## Decision
Option A, with a short built-in list of source-available licence names (Business Source License, Server Side Public
License, Elastic License, Commons Clause and similar) for the family check. Today's "NOASSERTION" or no licence
is always "to verify".

## Why
It works for projects nobody has listed yet. We accept one extra call per finalist.

## Revisit when
GitHub's API exposes licence history directly.

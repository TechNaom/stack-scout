# ADR 0003: Known vulnerabilities come from OSV.dev, with GitHub advisories as the fallback

Date: 2026-11-27. Status: proposed

## Context
R5 needs known vulnerabilities for each finalist. Vulnerability databases look up **packages** (an ecosystem and a
name, for example npm `express`), not repositories, so each finalist's package name comes from its manifest
(`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`), fetched by ADR 0002's query.

## Options

| Option | Fit | Cost | Effort | Lock-in | On failure |
|---|---|---|---|---|---|
| A. [OSV.dev `/v1/querybatch`](https://google.github.io/osv.dev/post-v1-querybatch): all finalists in one call, then `/v1/vulns/{id}` only for severity of the ones found | npm, PyPI, Go, Maven, crates.io and more; free; no key *(the no-key and no-limit points come from secondary sources, to confirm in Build)* | Rs 0 | Low | Low (open data) | Down or partial (a `next_page_token`): retry, then "to verify" |
| B. GitHub's advisory database through GraphQL (`securityVulnerabilities`) | Same token as ADR 0002 | Rs 0 | Low | GitHub | Counts against the GraphQL budget |

## Decision
Option A, and B only for a package OSV does not know. A finalist with no package (an application, not a library) is
reported as "no package: vulnerabilities not checkable", never as "clean".

## Why
One call covers all finalists and the main ecosystems. "Not checkable" is said out loud instead of implying safety.

## Revisit when
OSV adds limits or keys.

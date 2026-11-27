# PRD: Stack Scout

Version 1, 2026-11-27. Brief: [brief.md](brief.md). Numbers marked *(proposed)* are suggestions for the owner
to change.

## Users and their jobs
| User | Wants to | So that |
|---|---|---|
| Developer or architect with a SOW | get a stack they can defend | they start building on solid, living projects |
| Consultant or founder | compare options and cost quickly | they can quote and plan with confidence |
| Idea to Orbit (later) | call Stack Scout in Blueprint | each product's design starts from a researched stack |

## Requirements

| ID | Requirement | Priority | Acceptance check |
|---|---|---|---|
| R1 | Read a SOW from pasted text or a file (Markdown, text, PDF, **.docx**: the most common SOW format for consultants) | must | 4 sample SOWs in 4 formats are read in full |
| R2 | Find what the SOW leaves open that changes the stack (scale, users, data, budget, cloud, team skills, compliance, deadline, **whether the user will distribute the product**, which R6 needs) | must | On labelled test SOWs, the open points found match each SOW's expected list |
| R3 | **Interview** through Claude's question screen: multiple choice with the recommended option first, never asking what the SOW already says. The screen allows at most 4 questions at a time and 2-4 options each; every question has an "I don't know, use the default" path | must | 8 questions or fewer on a typical SOW *(proposed)*; no question answered by the SOW; a "use the default" answer appears as "assumed" in `stack.md` |
| R4 | Break the SOW into capabilities (for example "generate a memo", "store documents", "audit log") | must | Every SOW requirement maps to at least one capability |
| R5 | For each capability, find candidate open-source projects and **check each live**: exists, stars, licence, last push, archived, **latest release date, contributor count, and known vulnerabilities** (OSV.dev or GitHub security advisories, both free) | must | All facts match their source at run time, in 20 of 20 test SOWs *(proposed)*; a planted project with a known vulnerability is flagged |
| R6 | Drop dead or unsafe candidates: archived; no activity for 12 months *(proposed)*; a licence that conflicts with the user's use (for example AGPL in a product they distribute, using R2's answer), unless the user accepts it. A missing licence or GitHub's "NOASSERTION" is "to verify", never assumed open. Flag projects whose licence changed to a source-available one in the last 24 months *(proposed)* (as Redis, Terraform and Elastic did); GitHub's API returns only the current licence, so this needs the licence file's change history (Blueprint) | must | Planted dead, archived, unlicensed and relicensed projects are dropped or flagged |
| R7 | Write `stack.md`: the run date ("facts as of"), the stack per layer, each choice with its reason, one rejected alternative and why, verified projects with links and facts, risks, and a monthly cost estimate at the stated scale. When no open-source project is good enough for a capability, say so plainly: "build it yourself" or "use a managed service" | must | Template sections all filled for each test SOW; a capability with no good project gets the explicit outcome |
| R8 | Optionally write ADRs (`adr/NNNN-*.md`) in Idea to Orbit's format | should | Generated ADRs pass Idea to Orbit's ADR shape |
| R9 | Say what it could not verify (a price, a quota) instead of guessing, with "to verify" | must | Unverifiable facts are marked, never stated as fact |
| R10 | Sources: every fact about a project or a price carries its link | must | No unlinked fact in `stack.md` |
| R11 | Install on any Claude Code surface: `/plugin install`, or an install script where `/plugin` is missing | must | Install, rerun and uninstall pass on Windows, macOS and Linux in CI |
| R12 | A command (`/stack-scout`) and a skill that other plugins can call with a SOW path; it writes `stack.md` and a machine-readable **`stack.json`** next to it, so tools such as Idea to Orbit can read the result | must | Idea to Orbit reads `stack.json` in a test; `stack.json` validates against its schema |
| R13 | A CLI for users without Claude Code (bring your own API key) | could, later | n/a in version 1 |
| R14 | **Non-interactive mode** for callers with nobody to answer (R12): answers come from an input file, or the recommended defaults are used and every one is listed as "assumed" in `stack.md` and `stack.json` | must | A run with no person present finishes and lists its assumptions |
| R15 | **Managed services** in the stack (for example a hosted database, serverless functions, hosting) are each linked to the provider's official pricing page with the date checked, or marked "to verify"; the cost estimate (R7) uses only these | must | Every service in a test stack has a dated pricing link or "to verify" |
| R16 | **The picks fit together:** all layers share a compatible language, runtime and versions (for example no Python-only library in a Node backend, no clashing major versions); conflicts are fixed or shown | must | A test SOW that plants a mismatch gets it caught |

## Non-functional requirements

| ID | Area | Requirement | Acceptance check |
|---|---|---|---|
| N1 | Cost | Rs 0 for users beyond their own Claude plan; no paid API needed; our CI on free runners. Each run uses the user's Claude quota, so a run has a cap of about 200 tool calls *(proposed)*; checks are batched (for example several repositories in one GraphQL query) because a rough count is already about 96 calls for 8 capabilities x 3 candidates x 4 checks, before searches and pricing pages. If a run reaches the cap, it stops with a partial result and a note | No paid service in the code path; a capped run ends cleanly |
| N2 | Accuracy (AI eval bar) | No invented project, licence or star count; every fact from a live call | Eval scenarios with planted fake names fail if any fact is unverified |
| N3 | Security and privacy | A SOW may be confidential (consultants work under NDA): search queries are built **only from generic capability names**, never from client names, product names or project terms; nothing is sent to third parties beyond those queries and the user's own model; no telemetry | An eval that plants a client name finds it in no outgoing query |
| N4 | Performance | From paste to `stack.md`: at most 10 minutes of the user's own time (reading and answering) and about 30 minutes of clock time *(proposed)* | Timed on the test SOWs |
| N5 | Release | Versioned, tagged releases; CHANGELOG; a rollback is installing the previous tag | Release checklist |
| N6 | Guardrails | Never recommends a project it did not check this run; respects GitHub API limits (backs off, says when it is rate-limited) | Tests with a rate-limit response |
| N7 | Quality | Offline checks and pressure-scenario evals in CI, like Idea to Orbit | CI green on 3 platforms |

## Out of scope
Building or deploying the stack; paid data sources; private repositories; a web app; Idea to Orbit integration
(secondary plan).

## Success measures
| Measure | Target | By |
|---|---|---|
| Facts correct (projects, licences, stars) | 100% on 20 test SOWs *(proposed)* | first release |
| Confidential stays confidential | no client or project name in any outgoing query, in the planted-name eval | first release |
| The picks fit together | the planted mismatch is caught in every compatibility test SOW (R16) | first release |
| Owner rating on real SOWs | 4 of 5 or better on 5 SOWs *(proposed)* | first release |
| Outside users | no target for version 1 (stated plainly; revisited after the first release) | - |

## Risks and assumptions
| Risk or assumption | Impact | How we check or reduce it |
|---|---|---|
| GitHub search misses the best project for a niche | A weaker stack | Also search awesome-lists and the model's own knowledge, then verify every candidate live |
| GitHub API rate limits without a token | Slow or partial checks | Use the user's `gh` login when present; back off; say what was not checked |
| Stars are a weak quality signal | Popular but poor picks | Combine stars with recent activity, releases, issues answered, licence |
| Cost estimates drift | Wrong budget | Every price linked and dated; "to verify" when not found |
| Public SOWs are rare, so the 20 test SOWs (with labelled open points, a planted mismatch, a planted client name, planted dead and vulnerable projects) have to be written | Evals cannot start without them | A known task in Assemble: write and label the test SOWs first |

## Open questions
- ~~Licence for Stack Scout itself~~: **MIT** (owner, 2026-11-27).
- The exact eval bars marked *(proposed)* above (20 test SOWs, 8 questions, 200 tool calls, 10 and 30 minutes, 12 months, 24 months for relicensing).

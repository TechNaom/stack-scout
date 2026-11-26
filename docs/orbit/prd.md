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
| R1 | Read a SOW from pasted text or a file (Markdown, text, PDF) | must | 3 sample SOWs in 3 formats are read in full |
| R2 | Find what the SOW leaves open that changes the stack (scale, users, data, budget, cloud, team skills, compliance, deadline) | must | For each test SOW, the open points listed match a reviewer's list |
| R3 | **Interview** through Claude's question screen: multiple choice with a recommended option first, a few at a time, never asking what the SOW already says | must | 8 questions or fewer on a typical SOW *(proposed)*; no question answered by the SOW |
| R4 | Break the SOW into capabilities (for example "generate a memo", "store documents", "audit log") | must | Every SOW requirement maps to at least one capability |
| R5 | For each capability, find candidate open-source projects and **check each live**: exists, stars, licence, last push, archived | must | All facts match GitHub's API at run time, in 20 of 20 test SOWs *(proposed)* |
| R6 | Drop dead or unsafe candidates: archived; no activity for 12 months *(proposed)*; a licence that conflicts with the user's use (for example AGPL in a product they distribute), unless the user accepts it | must | Planted dead and archived projects never reach the stack |
| R7 | Write `stack.md`: the stack per layer, each choice with its reason, one rejected alternative and why, verified projects with links and facts, risks, and a monthly cost estimate at the stated scale | must | Template sections all filled for each test SOW |
| R8 | Optionally write ADRs (`adr/NNNN-*.md`) in Idea to Orbit's format | should | Generated ADRs pass Idea to Orbit's ADR shape |
| R9 | Say what it could not verify (a price, a quota) instead of guessing, with "to verify" | must | Unverifiable facts are marked, never stated as fact |
| R10 | Sources: every fact about a project or a price carries its link | must | No unlinked fact in `stack.md` |
| R11 | Install on any Claude Code surface: `/plugin install`, or an install script where `/plugin` is missing | must | Install, rerun and uninstall pass on Windows, macOS and Linux in CI |
| R12 | A command (`/stack-scout`) and a skill that other plugins can call with a SOW path and get `stack.md` back | should | Idea to Orbit can call it in a test |
| R13 | A CLI for users without Claude Code (bring your own API key) | could, later | n/a in version 1 |

## Non-functional requirements

| ID | Area | Requirement | Acceptance check |
|---|---|---|---|
| N1 | Cost | Rs 0 for users beyond their own Claude plan; no paid API needed; our CI on free runners | No paid service in the code path |
| N2 | Accuracy (AI eval bar) | No invented project, licence or star count; every fact from a live call | Eval scenarios with planted fake names fail if any fact is unverified |
| N3 | Security and privacy | The SOW never leaves the user's session except as search queries; nothing sent to third parties beyond GitHub search and the user's own model | Code review; no telemetry |
| N4 | Performance | A typical SOW, from paste to `stack.md`, in under 10 minutes of the user's time *(proposed)* | Timed on the test SOWs |
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
| Owner rating on real SOWs | 4 of 5 or better on 5 SOWs *(proposed)* | first release |
| Outside users | stars, installs or issues from people other than the owner | open |

## Risks and assumptions
| Risk or assumption | Impact | How we check or reduce it |
|---|---|---|
| GitHub search misses the best project for a niche | A weaker stack | Also search awesome-lists and the model's own knowledge, then verify every candidate live |
| GitHub API rate limits without a token | Slow or partial checks | Use the user's `gh` login when present; back off; say what was not checked |
| Stars are a weak quality signal | Popular but poor picks | Combine stars with recent activity, releases, issues answered, licence |
| Cost estimates drift | Wrong budget | Every price linked and dated; "to verify" when not found |

## Open questions
- Licence for Stack Scout itself: MIT *(proposed)*.
- The exact eval bars marked *(proposed)* above.

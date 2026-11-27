# Product state: Stack Scout

Started: 2026-11-27

## Current

- Stage: build
- Status: in progress   <!-- in progress | waiting for approval | approved | needs review -->

## Settings

- Code host: github (public repo TechNaom/stack-scout, created 2026-11-27 on the owner's go-ahead)
- Work branch: main *(proposed)*
- Release branch: main
- Promotion: none
- Builders: subagents
- Fast tests: filled at Assemble's T1 (no code yet)
- Full suite: filled at Assemble's T1
- CI: GitHub Actions on Linux, Windows and macOS *(proposed, as in Idea to Orbit)*
- Profile: startup (free, nothing hosted)

## Gates

| Stage | Status | Approved by | Date |
|---|---|---|---|
| ignite | approved | owner ("yes") | 2026-11-27 |
| blueprint | approved | owner ("yes proceed") | 2026-11-27 |
| assemble | approved | owner ("a,b,c": yes to Assemble with MIT) | 2026-11-27 |
| build | in progress | | |
| test-flight | not started | | |
| launch | not started | | |
| orbit | not started | | |

## Answers so far

- 2026-11-27 Owner: **public, open-source, reusable.** Anyone with a statement of work, on any problem (a memo
  generator, a regulatory filing system, a token guard, ...), uses it to build their own robust tech stack. It
  interviews the user with clear multiple-choice questions (like Claude Code's plan-mode questions), researches live
  GitHub repos, and finalises the stack.

- 2026-11-27 Owner: **a separate repo first.** Later, as a secondary plan, Idea to Orbit's planning stage
  (Blueprint) integrates it to suggest the tech stack. Design it so another tool can call it (a skill or a command
  with a clear input and output).

## Open questions

- ~~Licence for Stack Scout itself~~ MIT, owner 2026-11-27.
- The proposed numbers in the PRD: 20 test SOWs, 8 questions, about 200 tool calls per run, 10 minutes of the
  user's time and about 30 minutes of clock time, 12 months without activity counts as dead, 24 months for
  "recently relicensed".

## Log

- 2026-11-27 Assemble approved by the owner; licence MIT. Issues #1-#37 created (labels M1-M4). Build starts with T1 (#1).

- 2026-11-27 Assemble: tasks.md (4 milestones, 37 tasks, cards for M1's 12); two cold reads by fresh agents (12 + 11
  questions) answered on the cards and in architecture.md; Fast tests and Full suite fixed at T1. Waiting for
  approval, and for the owner's licence choice (MIT proposed).

- 2026-11-27 Blueprint approved by the owner ("yes proceed"); price check stays strict (current design). Public repo
  created and pushed on the owner's go-ahead. Assemble started.

- 2026-11-27 Blueprint second review (9/10) applied: ADR tables one line per row; private terms beat the
  tech-term allowlist (+ eval); fact-shaped text instead of all digits; licence ids and phrases, not bare words;
  deps.dev confirmed by a live call; bot-only history is "to verify". Price check: the design uses the strict version
  (architecture fix 6); the owner may switch it to the labelled version before approval. Waiting for approval.

- 2026-11-27 Blueprint: ADRs 0001-0007, architecture v1, cold read by a fresh agent (11 questions + unnamed parts) answered in architecture.md; waiting for approval.

- 2026-11-27 Ignite approved by the owner ("yes") after three review rounds. Blueprint started.

- 2026-11-27 Second review: priorities made consistent (R12 must), cap 200, relicence window, success rows; waiting for approval.
- 2026-11-27 Ignite review (8/10, five fixes plus smaller ones) applied to the brief and PRD; waiting for approval.
- 2026-11-27 Owner chose: plugin first, CLI later; full output with optional ADRs; name Stack Scout; separate repo (Idea to Orbit integration later). Brief and PRD written; waiting for approval.

- 2026-11-27 ignite started.

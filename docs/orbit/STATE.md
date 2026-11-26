# Product state: Stack Scout

Started: 2026-11-27

## Current

- Stage: ignite
- Status: waiting for approval   <!-- in progress | waiting for approval | approved | needs review -->

## Settings

- Code host: github (public repo TechNaom/stack-scout, to be created after the Ignite gate)
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
| ignite | waiting for approval | | |
| blueprint | not started | | |
| assemble | not started | | |
| build | not started | | |
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

- Licence for Stack Scout itself: MIT (proposed).
- The proposed eval bars in the PRD (20 test SOWs, 8 questions, 10 minutes, 12 months).

## Log

- 2026-11-27 Owner chose: plugin first, CLI later; full output with optional ADRs; name Stack Scout; separate repo (Idea to Orbit integration later). Brief and PRD written; waiting for approval.

- 2026-11-27 ignite started.

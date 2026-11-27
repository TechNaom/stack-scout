# Journal: Stack Scout

Every change and every roadblock, newest first. `STATE.md` says where the product is; this
file says what happened on the way and what it taught. The learn skill reads it.

| When | Kind | What | Commit |
|---|---|---|---|
| 2026-11-27 | Decision | **Blueprint approved** by the owner ("yes proceed"); price check strict; repo TechNaom/stack-scout created. | (this commit) |
| 2026-11-27 | Fix in review | **Blueprint second review (9/10) applied:** broken ADR tables rejoined; private terms beat the tech-term allowlist; fact-shaped text instead of all digits; licence ids and phrases, not bare words; deps.dev confirmed by a live call; bot-only history rule. Missed by: the first review's fixes (wrapped table rows, over-broad bans). | eab5dcb |
| 2026-11-27 | Fix in review | **Blueprint review (8.5/10) applied:** ADR 0006 made consistent; no facts in prose; tech-term allowlist for the guard; skill-level guard for the model's own searches (transcript eval); REST-only no-token mode; checked model-read prices; non-bot default-branch activity; deps.dev and Scorecard; licence path and renames; docx tables; assumed SOW-specific questions. Missed by: the first draft (one wrong claim: GraphQL without a token). | 90b8511 |
| 2026-11-27 | Fix in review | **Blueprint cold read:** 11 guesses and 14 unnamed parts found by a fresh agent, answered in architecture.md. Biggest: stdlib-only conflicted with YAML (now JSON); guard enforcement moved into code; the 200-call cap is skill-level, measured by evals. Missed by: the first draft. | ad69f29 |
| 2026-11-27 | Decision | **Ignite approved by the owner ("yes").** Blueprint next. | b08c661 |
| 2026-11-27 | Change | **Ignite second review applied:** R12 made a must (consistent with R14 and `stack.json`), 200-call cap with batched checks, 24-month relicence window, two success rows, STATE open questions updated. | ad917cc |
| 2026-11-27 | Change | **Ignite review applied** (owner-supplied review, 8/10): non-interactive mode (R14), managed services with dated pricing (R15), compatibility check (R16), security health (vulnerabilities, releases, contributors), confidential-safe queries (N3), .docx, "distribute?" question, licence edge cases, `stack.json`, run date, build-it-yourself outcome, tool-call cap, test SOWs as a known task. | 3b20224 |
| 2026-11-27 | Decision | **Separate public open-source repo, Claude Code plugin first, CLI later; output: stack, verified repos, reasons, risks, cost, optional ADRs; name Stack Scout.** Idea to Orbit integration later (secondary). | - |

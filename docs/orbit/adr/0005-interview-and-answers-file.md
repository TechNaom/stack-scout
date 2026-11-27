# ADR 0005: The interview uses Claude's question screen; non-interactive runs read an answers file

Date: 2026-11-27. Status: accepted

## Context
R3 (interview), R14 (non-interactive mode), R2 (open points). Claude Code's question tool shows at most 4 questions
at a time, each with 2 to 4 options, and the user can always type their own answer.

## Options

| Option | Fit | Cost | Effort | Lock-in | On failure |
|---|---|---|---|---|---|
| A. The skill finds the open points (R2), ranks them by how much they change the stack, and asks them on the question screen in rounds of up to 4, recommended option first, plus "I don't know, use the default". Non-interactive: `--answers answers.json`, or `--defaults`, which uses the recommended option for each and records it as assumed | Matches the owner's plan-mode style; callers with nobody present still get a result | Rs 0 | Low | Claude Code's question tool | Tool not available (another surface): the same questions as a numbered text list |
| B. Free-form chat questions | Works anywhere | Rs 0 | Low | None | Long, unstructured answers; harder to keep to 8 questions |

## Decision
Option A. The open points and their defaults come from one question bank (`skills/stack-scout/questions.json`), so
the interactive and non-interactive modes ask exactly the same things.

## Why
Structured choices are faster for the user and easier to test (the evals answer from the file). We depend on the
question tool, with a text fallback.

## Revisit when
The question tool's limits change.

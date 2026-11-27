# ADR 0001: A Claude Code plugin of skills plus small standard-library Python scripts

Date: 2026-11-27. Status: accepted

## Context
R11 (install on any Claude Code surface), R12 (a command and a skill other plugins can call), N1 (Rs 0 for users),
N2 (no invented facts). The interview and the reasoning need the user's model; the facts need deterministic code.

## Options

| Option | Fit | Monthly cost | Operating effort | Lock-in | On failure |
|---|---|---|---|---|---|
| A. Plugin: skills and a `/stack-scout` command for the conversation; Python 3 standard-library scripts (`scripts/`) for every fact (GitHub, OSV, licence history, compatibility, validation) | The model talks and reasons; code fetches and checks facts, so nothing is invented. No dependencies to install; same installers and CI as Idea to Orbit | Rs 0 | Low | Claude Code (a CLI later, R13) | A script error is reported with its message; the run stops instead of guessing |
| B. An MCP server that does everything | Callable from any MCP client | Rs 0, but a process to run | Medium: a server to package for 3 platforms | Low | Server down: nothing works |
| C. Skills only, the model fetches facts with its own web tools | Simplest | Rs 0 | Low | Claude Code | Facts can be misread or invented; breaks N2 |

## Decision
Option A. Python 3.10 or later is required (it is already needed by Idea to Orbit's checks); the installers say so.

## Why
Separating talking (model) from facts (code) is what makes "no invented projects" enforceable. Standard library only
means nothing to install. We give up MCP reach until the CLI (R13).

## Revisit when
Users ask for Stack Scout from non-Claude agents: wrap the same scripts in an MCP server or the CLI.

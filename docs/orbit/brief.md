# Brief: Stack Scout

**One line:** An open-source Claude Code plugin that takes any statement of work, interviews you with clear
multiple-choice questions, checks real open-source projects live on GitHub, and hands you a robust tech stack
with reasons, risks, cost and optional decision records.

## The problem
Picking a tech stack for a new statement of work (a memo generator, a regulatory filing system, a token guard,
anything) is slow and risky. People ask a chatbot and get a confident list with no reasons, names of projects
that are dead, archived or wrongly licensed, and no idea what it will cost. Or they spend days comparing options
by hand. Good choices depend on facts the SOW rarely states: scale, team skills, budget, cloud, compliance.

## Who it is for
- **Users:** developers, architects, consultants and founders who have a SOW or problem statement and need a
  stack they can defend. Open source, for anyone (owner, 2026-11-27).
- **Buyer:** none; free and MIT licensed *(proposed)*.
- **First user:** the owner, on real SOWs; later Idea to Orbit's Blueprint stage calls it.

## What changes when it works
"I paste my SOW, answer a few clear questions, and in minutes I have a stack I can defend: each choice with
its reason, real projects to build on that I know are alive and safely licensed, the risks, and what it costs
a month."

## Why now
Coding agents can now research live sources and ask structured questions in their own interface. Nothing
open-source does the whole job (the only dedicated tool found has 9 stars); our own Idea to Orbit already has
the engineering (installers, offline checks, evals, CI) to reuse.

## First version
1. A Claude Code plugin (owner, 2026-11-27: plugin first, CLI later).
2. Reads a SOW (pasted text or a file).
3. Interviews the user with Claude's question screen: few questions, only about what the SOW leaves open.
4. Breaks the SOW into capabilities; searches and checks candidate projects live (stars, licence, last
   activity, archived); drops dead or unsafe ones.
5. Writes `stack.md`: the stack per layer, each choice with its reason and one rejected alternative, verified
   projects, risks, and a monthly cost estimate at the stated scale; ADRs optional.

## Not in the first version
- The CLI for users without Claude Code (later).
- Building or deploying the stack.
- Paid market data (private benchmarks, paid pricing APIs).
- Idea to Orbit integration (a secondary plan, after the first version).

## How we will know it works *(proposed numbers)*
- **No invented projects:** every recommended repository exists and its stars, licence and last activity match
  GitHub at the time of the run, in 20 of 20 test SOWs.
- **No dead picks:** no archived project, and none without activity in the last 12 months unless stated as a
  deliberate choice.
- **Short interview:** 8 questions or fewer for a typical SOW.
- **Useful:** on 5 real SOWs, the owner rates the stack 4 out of 5 or better.

## Constraints
- Budget: Rs 0 to run for users (their own Claude plan); our CI on free runners.
- Public repository, MIT licence *(proposed)*.
- Works on Windows, macOS and Linux, like Idea to Orbit.
- Deadline: none stated.

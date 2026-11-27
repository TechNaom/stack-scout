# Tasks: Stack Scout

Version 1, 2026-11-27. Architecture: [architecture.md](architecture.md). PRD: [prd.md](prd.md).

## Milestones

| Milestone | Leaves the product able to | Tasks |
|---|---|---|
| M1 Walking skeleton | Be installed by script on Windows, macOS and Linux, and turn a Markdown SOW into a validated `stack.md` and `stack.json` with live GitHub facts (interview or `--defaults`) | T1-T12 |
| M2 Every must-have check | Read .docx SOWs, search GitHub, check vulnerabilities, Scorecard, licence history, prices and fit; full interview and non-interactive mode; optional ADRs | T13-T26 |
| M3 Evals | Prove the PRD's bars on 20 labelled SOWs: facts correct, nothing planted kept, no private name in any query, mismatch caught, question and call caps, timing | T27-T32 |
| M4 Release and operations | Ship v0.1.0 publicly with docs, a weekly live health check, a rehearsed rollback and the owner's rating | T33-T37 |

Product-wide conventions (every card follows them):
- **Python 3.10 or newer, standard library only**, in the scripts and the tests. Tests use `unittest`.
- **Builders run in Git Bash on Windows** (see Builders in `STATE.md`): forward slashes in every path, `python`
  not `python3`.
- **Fast tests:** `python -m unittest discover -s tests -t . -v`. **Full suite:** the fast tests, then
  `python tests/check.py`.
- **Everything the skill runs lives inside the skill folder** `skills/stack-scout/`: `skills/stack-scout/scripts/`, `skills/stack-scout/data/`,
  `skills/stack-scout/schema/`, `templates/` and `questions.json`. Each script finds the rest through
  `ROOT = pathlib.Path(__file__).resolve().parent.parent` (the skill folder). Claude Code tells the model every
  skill's folder ("Base directory for this skill: ..."), for a plugin install and a script install alike, so the
  skill sets `SS` to that folder and never depends on `${CLAUDE_PLUGIN_ROOT}` reaching the shell. The
  installers copy only the skill folder and the command. (Decided at the Assemble cold read; replaces
  architecture point 10's `<config>/stack-scout/` copy.) Below, `S/` is short for `skills/stack-scout/` **in prose
  only**; every file list and command spells the full path.
- Tests import `from tests import helpers` (written in T1), which puts `skills/stack-scout/scripts/` on
  `sys.path`; this works for both `python -m unittest discover -s tests -t . -v` and
  `python -m unittest tests.test_x -v` run from the repository root. `tests/check.py` is a plain script and
  does not import `helpers`. Tests never touch the network: every HTTP call goes to the mock server from T5,
  through the base-URL variables in `skills/stack-scout/scripts/common.py`.
- Every script prints one JSON object on stdout. Exit codes: 0 ok, 2 blocked or invalid, 3 rate-limited
  (partial results saved first). A script never prints a token.
- One task per branch `t<N>-<slug>`, one pull request into `main`, commits as Manohar Papasani with the noreply
  email.

## M1 Walking skeleton

| ID | Task | Serves | Test (written first) | Done check | Depends on | Size | Issue |
|---|---|---|---|---|---|---|---|
| T1 | Repository basics, licence and CI on 3 platforms | N5, N7 | `tests/test_repo.py`: CI file has the 3-OS matrix and runs both suites | CI green on Linux, Windows and macOS for the pull request | - | S | |
| T2 | Hand-written schemas and the schema checker | R12, N2 | `tests/test_schema.py`: good and bad examples for all 6 schemas | `python -m unittest tests.test_schema -v` OK | T1 | M | |
| T3 | First 5 labelled test SOWs | R2, N2, N3 | `tests/test_fixtures.py`: every SOW has a label entry that passes `labels.schema.json` | the fixture test is OK | T2 | M | |
| T4 | Shared core: clock, token, redaction, facts file, run meter | N1, N6, R9 | `tests/test_common.py` | the common test is OK | T1 | M | |
| T5 | HTTP client with back-off, and the mock API server | N6 | `tests/test_http.py` against `tests/mock_api.py` (200, 403, 429, Retry-After, 3 retries) | the http test is OK | T4 | M | |
| T6 | `guard.py` and its word lists | N3 | `tests/test_guard.py` incl. a private name that is also a tech term | the guard test is OK | T4 | M | |
| T7 | `facts.py verify`: batched GraphQL, REST-only mode, bot rule | R5, R6, N6 | `tests/test_facts_verify.py` against the mock server | the facts test is OK | T5, T6 | M | |
| T8 | `validate.py`: schema, subjects, required fields, prose rules | N2, R9, R10 | `tests/test_validate.py` with the good and bad prose lists | the validate test is OK | T2, T4 | M | |
| T9 | `render.py`: `stack.md` from `stack.json` and the facts file | R7, R9, R10 | `tests/test_render.py`: golden file, every fact linked | the render test is OK | T8 | M | |
| T10 | Starter question bank, the skill and the `/stack-scout` command | R2, R3, R4, R12, R14 | `tests/check.py`: skill and command shape, questions pass their schema | full suite OK | T2, T6, T7, T8, T9 | M | |
| T11 | Installers and their CI test | R11 | `tests/test_install.py`: install, rerun, uninstall into a temp config | CI green on 3 platforms | T10 | M | |
| T12 | End to end: live smoke and one real skill run | R1, R5, R7 | `tests/smoke_live.py` (skipped without a token) | live smoke prints `ok`; a fresh agent's skill run on SOW 01 writes a validated `stack.md` | T11, T3 | S | |

## M2 Every must-have check

| ID | Task | Serves | Test (written first) | Done check | Depends on | Size | Issue |
|---|---|---|---|---|---|---|---|
| T13 | `sow.py`: .docx paragraphs, headings and tables; .md and .txt; unreadable files exit 2 | R1 | `tests/test_sow.py` with .docx files built by the test from XML | sow test OK | T4 | M | |
| T14 | `facts.py search` (guard enforced in code) and contributor counts for finalists | R5, N3 | `tests/test_facts_search.py`: a blocked query makes no network call | search test OK | T7 | M | |
| T15 | deps.dev: repository to packages, OpenSSF Scorecard, manifest fallback | R5 | `tests/test_depsdev.py` incl. 404 fallback | test OK | T7 | M | |
| T16 | `osv.py`: querybatch, `next_page_token`, severity, "no package: not checkable" | R5 | `tests/test_osv.py` | test OK; `vulnerabilities` added to required fields | T15 | M | |
| T17 | `licence.py`: licence path, 24-month history, renames, family | R6 | `tests/test_licence.py` | test OK; `licence_history` required for finalists | T7 | M | |
| T18 | Licence-conflict rules with the "distribute" answer, and `accepted` | R6 | `tests/test_validate_licence.py` | test OK | T17, T8 | S | |
| T19 | `facts.py record-price` (strict) and `skills/stack-scout/data/pricing-urls.json`; services checked in `validate.py` | R15, R9 | `tests/test_price.py`: amount on the page kept, missing amount "to verify" | test OK | T5, T8 | M | |
| T20 | `skills/stack-scout/data/compat.json` and the compatibility rules in `validate.py` | R16 | `tests/test_compat.py`: a planted mismatch fails | test OK | T8, T15 | M | |
| T21 | Full question bank and `answers.json` rules | R2, R3, R14 | `tests/test_answers.py`: missing id assumed, unknown id error | test OK | T10 | M | |
| T22 | Skill full flow: question screens, text fallback, drop rules, build-yourself, private terms, guard on own searches, cap, `stack.prev`, `.gitignore` note | R3, R4, R6, R7, R14, N1, N3 | `tests/check.py` rules for every instruction | full suite OK | T13-T21 | M | |
| T23 | `--adr` output and the ADR shape check | R8 | `tests/test_adr.py` | test OK | T22 | S | |
| T24 | Token redaction across every script | N6, security | `tests/test_redaction.py` | test OK | T13-T19 | S | |
| T25 | Test SOWs 06-13 with labels (.docx, .txt, PDF; planted mismatch; client name that is a GitHub topic) | R1, R16, N3 | fixture test | test OK | T3, T13 | M | |
| T26 | Test SOWs 14-20 with labels (planted relicensed, vulnerable, bot-only, fake) | R5, R6, N2 | fixture test | test OK | T25 | M | |

## M3 Evals

| ID | Task | Serves | Test (written first) | Done check | Depends on | Size | Issue |
|---|---|---|---|---|---|---|---|
| T27 | Eval harness: cases in Idea to Orbit's format, a manual workflow with a cost ceiling, `tests/transcript_check.py` (queries, tool calls, questions) | N1, N3, N7 | `tests/test_transcript_check.py` on recorded transcripts | test OK | T22 | M | |
| T28 | Eval cases: planted fake, archived, dead, bot-only, vulnerable and relicensed projects never kept | N2, R5, R6 | the cases themselves | 1 run per case passes | T27, T26 | M | |
| T29 | Eval cases: planted client name, and one that is a GitHub topic, in no query or web search | N3 | the cases | passes | T27 | S | |
| T30 | Eval cases: mismatch caught, non-interactive run lists assumptions, 8 questions or fewer, about 200 calls or fewer, build-yourself outcome | R16, R14, R3, N1, R7 | the cases | passes | T27 | M | |
| T31 | Facts-correct scorer (re-fetch every rendered fact) and timed runs on all 20 SOWs | N2, N4, R5 | `tests/test_scorer.py` | report in `docs/eval-results.md` | T28-T30 | M | |
| T32 | `stack.json` consumer contract test (how Idea to Orbit reads it) | R12 | `tests/test_contract.py` | test OK | T22 | S | |

## M4 Release and operations

| ID | Task | Serves | Test (written first) | Done check | Depends on | Size | Issue |
|---|---|---|---|---|---|---|---|
| T33 | README, getting started, how it works, FAQ, CONTRIBUTING, SECURITY, CHANGELOG | N5 | `tests/check.py`: links resolve, no placeholder text | full suite OK | T31 | M | |
| T34 | Weekly API health workflow (live smoke on GitHub, OSV, deps.dev; a failure emails the owner) | N6, operations | `tests/test_repo.py` reads the workflow | one manual run green | T12, T16 | S | |
| T35 | Release checklist, `v0.1.0` tag and GitHub release | N5 | the checklist | release page live | T33 | S | |
| T36 | Rollback rehearsal: install the previous tag, by script and by `/plugin` | N5 | written steps | rehearsal recorded in `release.md` | T35 | S | |
| T37 | Owner rating on 5 real SOWs | success measure | - | 4 of 5 or better recorded | T35 | S | |

## Coverage

| Requirement | Tasks |
|---|---|
| R1 | T12 (Markdown), T13, T25 |
| R2 | T3, T10, T21 |
| R3 | T10, T21, T22, T30 |
| R4 | T10, T22 |
| R5 | T7, T12, T14, T15, T16, T26, T28, T31 |
| R6 | T7, T17, T18, T22, T26, T28 |
| R7 | T9, T12, T22, T30 |
| R8 | T23 |
| R9 | T4, T8, T9, T19 |
| R10 | T8, T9 |
| R11 | T11 |
| R12 | T2, T10, T32 |
| R13 | none: "could, later", not in version 1 (ADR 0001) |
| R14 | T10, T21, T22, T30 |
| R15 | T19 |
| R16 | T20, T25, T30 |
| N1 | T4, T22, T27, T30 |
| N2 | T2, T3, T8, T26, T28, T31 |
| N3 | T3, T6, T14, T22, T25, T27, T29 |
| N4 | T31 |
| N5 | T1, T33, T35, T36 |
| N6 | T4, T5, T7, T24, T34 |
| N7 | T1, T27 |

Gaps: R13 only, by design.

Operations: there is no server, so "operations" here means a weekly live health check of the three APIs we
depend on (T34), a backup tag and release per version (T35) and a rehearsed rollback (T36). The budget guard is the
run meter and the 200-call cap (T4, T22, T30); our own spend is Rs 0, and the manual eval workflow has a cost
ceiling (T27).

## Task cards (M1)

### T1 Repository basics, licence and CI on 3 platforms

Serves: N5, N7. Depends on: none. Size: S. Issue: <#>

**Files**
- Create: `LICENSE` (MIT, "Copyright (c) 2026 Manohar Papasani"), `README.md` (one paragraph from
  `docs/orbit/brief.md`'s one line, plus "Status: in development, not ready to install"), `.gitignore`,
  `.gitattributes`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `.github/workflows/check.yml`, `tests/__init__.py` (empty), `tests/helpers.py`, `tests/check.py`.
- Change: `docs/orbit/STATE.md` (Fast tests and Full suite, step 6).
- Test: `tests/test_repo.py`.

**Tests that read these files:** none (first code in the repository).

**Interfaces**
- `tests/helpers.py`: `ROOT: pathlib.Path` (the repository root), `SKILL = ROOT/"skills"/"stack-scout"`;
  importing it inserts `str(SKILL/"scripts")` at the front of `sys.path`; `def tmpdir() -> pathlib.Path` returns
  a new temporary folder removed at exit (`atexit` + `shutil.rmtree(..., ignore_errors=True)`).
- `tests/check.py`: run as `python tests/check.py`; prints `ok: <n> checks` and exits 0, or prints each failure
  as `FAIL: <message>` and exits 1. In T1 it makes exactly 7 checks: (1) `plugin.json` parses; (2)
  `marketplace.json` parses; (3) `plugin.json` `name` is `stack-scout`; (4) `marketplace.json`
  `plugins[0].name` is `stack-scout`; (5) `plugin.json` `version`, `marketplace.json` `metadata.version` and
  `plugins[0].version` are all equal (`0.0.1`); (6) `plugin.json` `license` is `MIT`; (7) `LICENSE` exists.

**Steps**
1. Write `tests/helpers.py` and `tests/test_repo.py::test_ci_matrix`: load `.github/workflows/check.yml` as text
   and assert it contains `ubuntu-latest`, `windows-latest`, `macos-latest`, `"3.10"`, `"3.12"`,
   `python -m unittest discover -s tests -t . -v` and `python tests/check.py`. (Text checks, because the standard
   library has no YAML parser.)
   Run `python -m unittest tests.test_repo -v`. Expect: `FAILED (errors=1)` with `FileNotFoundError`.
2. Write `.github/workflows/check.yml`: on push and pull_request, `permissions: contents: read`, matrix as above
   with `fail-fast: false`, steps `actions/checkout@v4`, `actions/setup-python@v5`, then the two commands.
   Run the test again. Expect: `OK`.
3. Write `.claude-plugin/plugin.json` (name `stack-scout`, version `0.0.1`, description from the brief's one
   line, author `{"name": "Manohar Papasani", "url": "https://github.com/TechNaom"}`, homepage and repository
   `https://github.com/TechNaom/stack-scout`, license `MIT`), `marketplace.json` (copy the shape of
   `idea-to-orbit/.claude-plugin/marketplace.json`, owner "TechNaom AI R&D Labs"), `LICENSE`, `README.md`,
   `.gitignore` (`.env`, `.env.*`, `!.env.example`, `__pycache__/`, `.stack-scout/`, `evals/results/`, `.DS_Store`)
   and `.gitattributes` (`*.sh text eol=lf`, `*.py text eol=lf`). The licence is MIT only after the owner
   confirms it at the Assemble gate; if they choose another, use that.
4. Write `tests/check.py` with the T1 checks. Run `python tests/check.py`. Expect: `ok: 7 checks`.
5. Run the full suite: `python -m unittest discover -s tests -t . -v && python tests/check.py`. Expect: `OK`, then
   `ok: 7 checks`.
6. Set **Fast tests** and **Full suite** in `docs/orbit/STATE.md` to the two commands in the conventions above.
7. Commit `T1: repository basics, licence and CI on 3 platforms`, push the branch, open the pull request.

**Done check:** `gh pr checks` on the pull request. Expect: 6 checks (3 platforms x 2 Python versions), all `pass`.

**Also, a CI change:** `tests/test_repo.py::test_ci_matrix` fails if the matrix or either command is removed.

**Watch out:** Windows runners use PowerShell by default; the two commands work in both shells, so set no
`shell:`. Keep `plugin.json` free of fields Claude Code does not know.

### T2 Hand-written schemas and the schema checker

Serves: R12, N2. Depends on: T1. Size: M. Issue: <#>

**Files**
- Create: `skills/stack-scout/schema/stack.schema.json`, `skills/stack-scout/schema/facts.schema.json`, `skills/stack-scout/schema/run.schema.json`,
  `skills/stack-scout/schema/questions.schema.json`, `skills/stack-scout/schema/answers.schema.json`, `skills/stack-scout/schema/labels.schema.json`, `skills/stack-scout/scripts/schema.py`.
- Test: `tests/test_schema.py`, examples in `tests/fixtures/schema/<name>.good.json` and
  `<name>.bad-<reason>.json`.

**Tests that read these files:** `tests/check.py` (none of these files yet). Later: T3, T8, T10, T21.

**Interfaces**
- `schema.validate(instance, schema) -> list[str]`: error messages, each starting with a JSON path such as
  `$.layers[0].reason: required`; empty list when valid. Supports only `type` (incl. a list of types),
  `required`, `properties`, `additionalProperties` (false or a schema), `items`, `enum`, `pattern`, `minimum`,
  `maximum`, `minItems`, `maxItems`. An unknown keyword raises `ValueError("unsupported keyword: <k>")`, so a
  schema can't silently ask for more than the checker does.
- `schema.load(name) -> dict`: reads `ROOT/"schema"/f"{name}.schema.json"`.
- CLI: `python skills/stack-scout/scripts/schema.py <name> <file>` prints `{"ok": true}` (exit 0) or
  `{"ok": false, "errors": [...]}` (exit 2).

**Shapes** (from architecture.md, "Implementation decisions" point 1; every object has
`"additionalProperties": false` unless stated):
- `facts`: `{"schema": 1, "facts": [Fact]}`. Fact: `subject` (pattern `^(github:[^/\s]+/[^/\s]+|osv:[^/\s]+/\S+|price:\S+)$`),
  `field` (string), `value` (any type, may be null), `source` (string, pattern `^https://`), `fetched_at`
  (pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`), `by` (enum `script`, `model-read`), optional `to_verify`
  (string: why the value could not be checked; `value` is then null). Required: all but `to_verify`.
- `stack`: as in the architecture. **Every top-level key is required:** `schema` (enum `[1]`), `facts_as_of`
  (pattern `^\d{4}-\d{2}-\d{2}$`), `partial` (boolean), `unchecked` (list of strings, may be empty),
  `assumed` (list of `{"id", "answer", "question"}`; `question` optional, set for the model's own SOW-specific
  questions), `layers`, `capabilities`, `accepted` (list of `{"subject", "what"}`, may be empty), `cost`.
  `layers[]` require `layer`, `choice`, `reason`, `alternative` (`{"name", "why_not"}`, both required),
  `projects`, `services`, `risks` (the three lists may be empty). `projects[]` and `services[]` are
  `{"subject"}` only: projects `github:owner/repo`, services `price:<service>`. **`capabilities[]` require
  `id`, `name`, `layer` (the `layer` value of the layer that serves it) and `outcome`** (enum `project`,
  `service`, `build-yourself`). `cost` requires `monthly_estimate` (number or null), `currency` (string),
  `parts` (`[{"subject", "monthly"}]`, `monthly` a number), `unknown_parts` (list of subjects).
- `run`: `schema`, `started`, `ended` (null while running), `script_calls`, `github_points`, `questions_asked`,
  `partial`.
- `questions`: a list of `{"id" (pattern `^[a-z_]+$`), "ask", "options" (2-4 strings), "default" (one of the
  options: checked in code, not by the schema), "changes" (list of layer names), "rank" (integer >= 1)}`.
- `answers`: an object whose values are strings (`additionalProperties: {"type": "string"}`).
- `labels`: a list of `{"id", "file", "format" (enum md, txt, docx, pdf), "open_points" (list of question ids),
  "capabilities_min" (integer), "planted": {"client_name", "client_name_is_topic", "mismatch", "fake",
  "archived", "dead", "bot_only", "relicensed", "vulnerable"}}`; every `planted` key optional; the lists hold
  `owner/repo` strings; `client_name` a string; `mismatch` a string describing it.

**Steps**
1. Write `tests/test_schema.py`: for each of the 6 schemas, the `.good.json` example gives no errors and each
   `.bad-*.json` gives at least one error whose path the file name names (for example
   `stack.bad-missing-reason.json` gives an error containing `reason`). Also: an unknown keyword raises
   `ValueError`. Run `python -m unittest tests.test_schema -v`. Expect: errors, `ModuleNotFoundError: No module
   named 'schema'`.
2. Write `skills/stack-scout/scripts/schema.py`. Run again. Expect: failures for the missing schema files.
3. Write the 6 schemas and the examples (at least 2 bad examples per schema). Run again. Expect: `OK`.
4. Full suite. Expect: `OK` and `ok: 7 checks`. Commit `T2: hand-written schemas and the schema checker`.

**Done check:** `python -m unittest tests.test_schema -v`. Expect: `OK`, at least 13 tests.

**Watch out:** `pattern` uses `re.search`, like JSON Schema; anchor patterns with `^...$`. `type: "integer"`
must reject `true` (a Python bool is an int). Report every error, not only the first.

### T3 First 5 labelled test SOWs

Serves: R2, N2, N3. Depends on: T2. Size: M. Issue: <#>

**Files**
- Create: `tests/fixtures/sows/01-memo-generator.md`, `02-regulatory-filing.md`, `03-token-guard.md`,
  `04-support-ticket-triage.md`, `05-document-search.md`, and `tests/fixtures/sows/labels.json`.
- Test: `tests/test_fixtures.py`.

**Tests that read these files:** none yet. Later: T12, T25-T31.

**Interfaces**
- `labels.json` passes `skills/stack-scout/schema/labels.schema.json` (T2). The open-point ids are the ones in T10's starter bank:
  `private_names`, `distribute`, `language`, `cloud`, `scale`, `budget`.

**Steps**
1. Write `tests/test_fixtures.py`: `labels.json` passes its schema; every label's `file` exists; every SOW file
   in the folder has exactly one label; every `open_points` id is one of the six above; any `planted.client_name`
   appears in its SOW's text. Run `python -m unittest tests.test_fixtures -v`. Expect: a failure,
   `labels.json` not found.
2. Write the 5 SOWs: 300-800 words each, realistic and invented (no real client), each with a scope, 5-10
   requirements, and gaps a consultant would ask about. Each SOW states some of the six points and leaves the
   others open; the label lists the open ones. SOW 02 plants a client name (an invented company, for example
   "Halvorsen Freight"); SOW 05 says "must run on Azure" (a tech term that must stay searchable).
3. Write `labels.json`. Run the test. Expect: `OK`.
4. Full suite, then commit `T3: first 5 labelled test SOWs`.

**Done check:** `python -m unittest tests.test_fixtures -v`. Expect: `OK`.

**Watch out:** no real company or person names except technology products. Planted projects (archived, dead,
bot-only, relicensed, vulnerable) come in T25-T26, after the scripts that check them exist; leave `planted` to
`client_name` only here.

### T4 Shared core: clock, token, redaction, facts file, run meter

Serves: N1, N6, R9. Depends on: T1. Size: M. Issue: <#>

**Files**
- Create: `skills/stack-scout/scripts/common.py`, `skills/stack-scout/data/rules.json`. Test:
  `tests/test_common.py`.

**Tests that read these files:** none yet. Every later script imports it.

**Interfaces** (all in `skills/stack-scout/scripts/common.py`)
- `EXIT_OK = 0`, `EXIT_BLOCKED = 2`, `EXIT_RATE_LIMITED = 3`.
- `now_utc() -> str` (`2026-11-27T10:00:00Z`) and `today_utc() -> str` (`2026-11-27`). When the environment
  variable `STACK_SCOUT_NOW` is set (same format as `now_utc`), both use it: tests fix the clock this way.
- `state_dir() -> pathlib.Path`: `$STACK_SCOUT_DIR` if set, else `./.stack-scout`; created if missing.
- `get_token() -> str | None`: `$GITHUB_TOKEN` if non-empty, else the output of `gh auth token` (subprocess,
  timeout 5 s, stripped); any failure or a missing `gh` returns None, never raises. `$STACK_SCOUT_NO_GH=1` skips
  `gh` (tests).
- `redact(text: str, token: str | None) -> str`: replaces every occurrence of the token with `***`.
- `run_day() -> str`: the date part of `run.json`'s `started` when `run.json` exists, else `today_utc()`. A run
  that crosses UTC midnight (5:30 AM IST) keeps one facts file, and `stack.json`'s `facts_as_of` is this date.
- `facts_path(day: str | None = None) -> pathlib.Path`: `state_dir()/f"facts-{day or run_day()}.json"`.
- `load_rules() -> dict`: reads `ROOT/"data"/"rules.json"`.
- `skills/stack-scout/data/rules.json` (written in this task, read by T7, T8 and the skill): `{"dead_after_months": 12,
  "relicence_window_months": 24, "tool_call_cap": 200, "max_questions": 8, "bot_window_commits": 100,
  "required_fields": ["exists", "stars", "licence", "last_activity", "archived", "latest_release"],
  "bot_logins": ["dependabot", "renovate", "github-actions", "pre-commit-ci", "mergify", "allcontributors",
  "snyk-bot", "imgbot"]}`. M2 tasks add to `required_fields`.
- `load_facts(path) -> list[dict]`: `[]` when the file is missing.
- `add_facts(new: list[dict], path=None) -> None`: merges by `(subject, field)`; the later `fetched_at` wins
  (equal: the new one wins); writes `{"schema": 1, "facts": [...]}` sorted by subject then field, UTF-8,
  2-space indent, through a temp file and `os.replace`.
- `fact(subject, field, value, source, by="script", to_verify=None) -> dict`: builds one fact stamped
  `now_utc()`; with `to_verify`, `value` is forced to None.
- `meter(script_calls: int = 1, github_points: int = 0, questions_asked: int = 0, partial: bool | None = None)`:
  creates `state_dir()/"run.json"` with `started = now_utc()` on first use, adds the counts, sets `partial` when
  given.
- `emit(obj: dict) -> None`: `print(json.dumps(obj, ensure_ascii=False))`.

**Steps**
1. Write `tests/test_common.py` (each test sets `STACK_SCOUT_DIR` to `helpers.tmpdir()`, `STACK_SCOUT_NOW`,
   `STACK_SCOUT_NO_GH=1`): fixed clock; token from env; no token gives None; redaction; merge keeps the newer
   value and the new one on a tie; the file passes `facts.schema.json`; `fact(..., to_verify="x")` has value
   None; `meter` twice gives `script_calls == 2` and one `started`; with `run.json` started on 2026-11-27T23:59:00Z and
   the clock moved to 2026-11-28T00:01:00Z, `facts_path()` still ends in `facts-2026-11-27.json`; `load_rules()`
   has the 9 keys. Run
   `python -m unittest tests.test_common -v`. Expect: `ModuleNotFoundError: No module named 'common'`.
2. Write `skills/stack-scout/scripts/common.py`. Run again. Expect: `OK`.
3. Full suite, commit `T4: shared core`.

**Done check:** `python -m unittest tests.test_common -v`. Expect: `OK`, at least 8 tests.

**Watch out:** never log or print the token; `redact` must handle `None`. Write files with `newline="\n"` so
Windows and Linux produce the same bytes.

### T5 HTTP client with back-off, and the mock API server

Serves: N6. Depends on: T4. Size: M. Issue: <#>

**Files**
- Change: `skills/stack-scout/scripts/common.py` (add the HTTP part). Create: `tests/mock_api.py`. Test: `tests/test_http.py`.

**Tests that read these files:** `tests/test_common.py` (imports `common`; must stay green).

**Interfaces**
- `GITHUB_API = os.environ.get("STACK_SCOUT_GITHUB_API", "https://api.github.com")`, and likewise
  `OSV_API` (`STACK_SCOUT_OSV_API`, `https://api.osv.dev`) and `DEPSDEV_API` (`STACK_SCOUT_DEPSDEV_API`,
  `https://api.deps.dev`). Read at call time, not import time, so tests can change them.
- `class RateLimited(Exception)`: has `.status` and `.reset_at` (epoch seconds or None).
- `http_json(method: str, url: str, body: dict | None = None, token: str | None = None, retries: int = 3)
  -> tuple[int, dict | list | None]`: `urllib.request`, 30 s timeout, `User-Agent: stack-scout`,
  `Authorization: Bearer <token>` when given, JSON body and response. 200-299 and 404 return
  `(status, parsed or None)`. 403 with `x-ratelimit-remaining: 0`, and any 429, wait (the `Retry-After` header,
  else until `x-ratelimit-reset`, at most 60 s, else 2, 4, 8 s) and retry up to `retries` times, then raise
  `RateLimited`. Other errors raise `RuntimeError(redact(message, token))`. `$STACK_SCOUT_NO_SLEEP=1` turns the
  waits into no-ops (tests).
- `tests/mock_api.py`: `class MockAPI` (context manager) starts `http.server.ThreadingHTTPServer` on port 0 in a
  thread; `.url` is its base URL; `.route(method, path, responses)` queues a list of
  `(status, headers: dict, body: dict | None)` returned in order (the last one repeats). **Routes match the path
  without the query string** (`/repos/o/r/commits` matches `/repos/o/r/commits?per_page=100`); an unrouted path
  returns 404 `{"message": "Not Found"}`. `.requests` records `(method, full path with query, headers, body)`
  for every call.

**Steps**
1. Write `tests/test_http.py`: 200 returns the body; 404 returns `(404, ...)`; one 429 then 200 succeeds after
   one retry; four 403s with `x-ratelimit-remaining: 0` raise `RateLimited` after exactly 4 requests; the token
   is sent in the header and never appears in a `RuntimeError` from a 500. Run
   `python -m unittest tests.test_http -v`. Expect: `ImportError` for `mock_api`.
2. Write `tests/mock_api.py`. Run again. Expect: failures, `http_json` missing.
3. Add the HTTP part to `common.py`. Run again. Expect: `OK`. Run `python -m unittest tests.test_common -v`.
   Expect: `OK`.
4. Full suite, commit `T5: HTTP client with back-off and the mock API`.

**Done check:** `python -m unittest tests.test_http -v`. Expect: `OK`, at least 5 tests, in under 10 s.

**Watch out:** a 403 without `x-ratelimit-remaining: 0` is a permission error, not a rate limit: raise
`RuntimeError` at once. Shut the mock server down in `__exit__`, or Windows runners hang.

### T6 `guard.py` and its word lists

Serves: N3. Depends on: T4. Size: M. Issue: <#>

**Files**
- Create: `skills/stack-scout/scripts/guard.py`, `skills/stack-scout/data/common-words.txt`,
  `skills/stack-scout/data/tech-terms.txt`. Test: `tests/test_guard.py`. (The CLI reads the `private_names`
  options from `skills/stack-scout/questions.json`, written in T10; until then, and when it is missing, it uses
  `["None", "I'll type them"]`.)

**Tests that read these files:** none yet. Later: T7 and T14 import `guard`.

**Interfaces**
- `load_words(name) -> set[str]`: lower-cased lines of `ROOT/"data"/name`, `#` comments and blank lines skipped.
- `extract_terms(sow_text: str, common: set[str], tech: set[str]) -> set[str]`: every capitalised word
  (`[A-Z][A-Za-z0-9&'.-]*`, trailing `.` dropped) and every run of 2+ consecutive capitalised words, kept only
  when its lower-case form is in neither `common` nor `tech`. All-capital words of 2-6 letters (acronyms such as
  "HFX") are kept unless in `tech`.
- `check(query: str, private: set[str], extracted: set[str], tech: set[str]) -> list[str]`: the hits, empty when
  allowed. **Private terms are checked first and always block, even when they are in `tech`.** Extracted terms
  block unless in `tech`. Matching is case-insensitive on whole words: `(?<![\w-])<escaped term>(?![\w-])`.
- `private_from_answers(answers: dict, options: list[str]) -> set[str]`: splits the `private_names` answer on
  commas and semicolons, trimmed, empty parts dropped, and **drops any part equal (case-insensitive) to one of
  that question's option labels** (`options`, read from `questions.json` by the CLI), so "None" or "I'll type
  them" never become terms. The typed names arrive as the free-text answer ("Other" on the question screen).
- CLI:
  - `python skills/stack-scout/scripts/guard.py terms --sow FILE [--private-terms FILE] [--answers FILE]` writes
    `state_dir()/"terms.json"` as `{"private": [...], "extracted": [...]}` and prints
    `{"ok": true, "private": <n>, "extracted": <n>}` (counts only).
  - `python skills/stack-scout/scripts/guard.py check "<query>"` reads `terms.json` (missing: exit 2,
    `{"ok": false, "error": "run guard.py terms first"}`); prints `{"ok": true}` (exit 0) or
    `{"ok": false, "hits": [...]}` (exit 2).

**Steps**
1. Write `tests/test_guard.py` with these cases (all must pass):
   - SOW text "Halvorsen Freight needs a memo tool. It must run on Azure." with an empty private list:
     extracted contains "Halvorsen", "Halvorsen Freight", not "Azure", not "It"; `check("memo generator azure")`
     is allowed; `check("Halvorsen memo generator")` is blocked.
   - private `{"Salesforce"}`, `tech` containing "salesforce": `check("salesforce crm connector")` is blocked
     (private beats the allowlist).
   - whole words: private `{"Acme"}` does not block "acmetools"; does block "ACME tools".
   - `private_from_answers({"private_names": "Halvorsen; Project Kite, "}, ["None", "I'll type them"])` gives
     `{"Halvorsen", "Project Kite"}`; `private_from_answers({"private_names": "None"}, ["None", "I'll type them"])`
     gives an empty set.
   - CLI: `terms` then `check` round trip through `subprocess`, with `STACK_SCOUT_DIR` set to a temp folder;
     exit codes 0 and 2.
   Run `python -m unittest tests.test_guard -v`. Expect: `ModuleNotFoundError: No module named 'guard'`.
2. Write `skills/stack-scout/data/common-words.txt`: the 1,000 most common English words, one per line, plus month and day names
   (source noted in its first comment line: write the list yourself or take a public-domain list such as
   Wiktionary's frequency lists, and name it). Write `skills/stack-scout/data/tech-terms.txt`: at least 300 technology names,
   one per line, lower case: GitHub's featured topics (`https://github.com/topics`), clouds and services (azure,
   aws, gcp, s3, ec2, lambda), languages, databases, frameworks. Its first comment line names the source and
   date. Company names that are also topics (stripe, shopify, salesforce) **stay in**; the private rule handles
   them.
3. Write `skills/stack-scout/scripts/guard.py`. Run the test. Expect: `OK`.
4. Full suite, commit `T6: guard and word lists`.

**Done check:** `python -m unittest tests.test_guard -v`. Expect: `OK`, at least 6 tests.

**Watch out:** sentence-start words ("The", "We") are in `common-words.txt`, which is what keeps them out. A
false positive only makes a query more generic, which is safe; a false negative leaks, so when unsure, block.
Never print the SOW text.

### T7 `facts.py verify`: batched GraphQL, REST-only mode, bot rule

Serves: R5, R6, N6. Depends on: T5, T6. Size: M. Issue: <#>

**Files**
- Create: `skills/stack-scout/scripts/facts.py`. Read: `skills/stack-scout/data/rules.json` (from T4). Test:
  `tests/test_facts_verify.py`.

**Tests that read these files:** `tests/test_common.py`, `tests/test_http.py` (import `common`).

**Interfaces**
- `is_bot(login: str | None, name: str | None) -> bool`: true when the login ends with `[bot]`, or the login or
  name (lower case, `[bot]` removed) is in `bot_logins`.
- `verify(repos: list[str]) -> dict`: the facts for each `owner/repo`, saved with `common.add_facts`, and returns
  `{"ok": true, "checked": [...], "missing": [...], "unchecked": [...], "partial": false, "mode": "graphql" | "rest"}`.
- **With a token (GraphQL):** one `POST {GITHUB_API}/graphql` per 20 repositories, each repository an alias
  (`r0`, `r1`, ...) asking for `url stargazerCount isArchived licenseInfo { spdxId }
  latestRelease { publishedAt } primaryLanguage { name } defaultBranchRef { target { ... on Commit {
  history(first: 100) { nodes { committedDate author { name user { login } } } } } } }`, plus
  `rateLimit { cost remaining resetAt }`. A null alias with a `NOT_FOUND` error means `exists = false` (and no
  other facts). Facts written (subject `github:owner/repo`, source `https://github.com/owner/repo`): `exists`,
  `stars`, `archived`, `licence` (the SPDX id; `NOASSERTION` or no licence: value null and
  `to_verify = "no licence GitHub can identify"`), `latest_release` (date `YYYY-MM-DD` or null with no
  `to_verify`: "no releases" is a fact), `primary_language`, `last_activity` (date of the newest commit whose
  author is not a bot; if all 100 are bots, value null and `to_verify = "only bot activity in the last 100
  commits"`). `meter(github_points=rateLimit.cost)`.
- **Without a token (REST only):** per repository `GET /repos/{owner}/{repo}` (404: `exists = false`) and
  `GET /repos/{owner}/{repo}/commits?per_page=100`; writes `exists`, `stars`, `archived`, `licence`
  (`license.spdx_id`), `last_activity`; `latest_release` and `primary_language` written with
  `to_verify = "needs a GitHub sign-in: run gh auth login"`. Output has `"mode": "rest"` and a `note` saying so.
- **A GraphQL rate limit can arrive as HTTP 200** with `errors[].type == "RATE_LIMITED"`: `facts.py` raises
  `common.RateLimited` for it, the same as a 403 or 429.
- `facts.py to-verify SUBJECT FIELD "REASON" --source URL`: writes one fact with value null and `to_verify`
  (for anything the run could not check yet, for example `price:openai-api price "pricing not checked yet"
  --source https://openai.com/api/pricing/`). The source must start with `https://`; otherwise exit 2.
- `RateLimited` from `http_json`: save what is done, add the rest to `unchecked`, print with `"partial": true`,
  `meter(partial=True)`, exit 3.
- CLI: `python skills/stack-scout/scripts/facts.py verify owner/repo [owner/repo ...]`; a malformed name exits 2 with
  `{"ok": false, "error": "not owner/repo: <arg>"}`.

**Steps**
1. Write `tests/test_facts_verify.py` against `MockAPI` (`STACK_SCOUT_GITHUB_API` set to its url,
   `STACK_SCOUT_NO_SLEEP=1`, a temp `STACK_SCOUT_DIR`, `GITHUB_TOKEN=test-token`):
   - 2 repositories in 1 GraphQL request; facts saved; `run.json` has the points.
   - 21 repositories make 2 requests.
   - a commit history of only `dependabot[bot]` and `renovate` gives `to_verify` "only bot activity in the last
     100 commits"; a history with a human commit after bots gives that human's date.
   - a NOT_FOUND alias gives `exists = false` and appears in `missing`.
   - `NOASSERTION` gives value null with `to_verify`.
   - no token (`GITHUB_TOKEN=""`, `STACK_SCOUT_NO_GH=1`): REST requests only, `"mode": "rest"`,
     `latest_release` has `to_verify`.
   - 429 on every request: exit 3, `"partial": true`, the facts from before the limit kept.
   - HTTP 200 with `{"errors": [{"type": "RATE_LIMITED"}]}`: exit 3 as well.
   - `to-verify price:x price "not checked" --source https://example.com/pricing` writes a null fact with
     `to_verify`; a `http://` source exits 2.
   Run `python -m unittest tests.test_facts_verify -v`. Expect: `ModuleNotFoundError: No module named 'facts'`.
2. Write `skills/stack-scout/scripts/facts.py`. Run again. Expect: `OK`.
3. Full suite, commit `T7: facts verify`.

**Done check:** `python -m unittest tests.test_facts_verify -v`. Expect: `OK`, at least 9 tests.

**Watch out:** a GraphQL response can be HTTP 200 with an `errors` list and partial `data`: handle each alias on
its own. Dates in facts are `YYYY-MM-DD` (UTC). `facts.py` does not run `guard.py` for `verify` (repository names
are public and come from GitHub); T14's `search` will.

### T8 `validate.py`: schema, subjects, required fields, prose rules

Serves: N2, R9, R10. Depends on: T2, T4. Size: M. Issue: <#>

**Files**
- Create: `skills/stack-scout/scripts/validate.py`, `skills/stack-scout/data/licences.json`. Test: `tests/test_validate.py`, fixtures in
  `tests/fixtures/validate/`.

**Tests that read these files:** `tests/test_schema.py` (uses `skills/stack-scout/schema/stack.schema.json`; unchanged here).

**Interfaces**
- `skills/stack-scout/data/licences.json`: `{"ids": {"MIT": "permissive", "Apache-2.0": "permissive", "BSD-2-Clause": "permissive",
  "BSD-3-Clause": "permissive", "ISC": "permissive", "MPL-2.0": "copyleft", "LGPL-3.0-only": "copyleft",
  "GPL-2.0-only": "copyleft", "GPL-3.0-only": "copyleft", "AGPL-3.0-only": "copyleft", "BUSL-1.1":
  "source-available", "SSPL-1.0": "source-available", "Elastic-2.0": "source-available"}, "phrases": {"MIT
  License": "permissive", "Apache License": "permissive", "BSD License": "permissive", "Mozilla Public License":
  "copyleft", "GNU General Public License": "copyleft", "GNU Affero General Public License": "copyleft",
  "GNU Lesser General Public License": "copyleft", "Business Source License": "source-available", "Server Side
  Public License": "source-available", "Elastic License": "source-available", "Commons Clause":
  "source-available"}}`. Add the `-or-later` forms of the GPL family ids.
- `prose_errors(text: str, licences: dict) -> list[str]`: the fact-shaped pieces found. Rejects: counts with a
  k or M suffix (`\b\d+(?:\.\d+)?\s?[kKmM]\b`), grouped numbers (`\b\d{1,3}(?:,\d{3})+\b`), a number followed by
  stars, forks, downloads, contributors, commits, users or issues; percentages (`%`, "percent"); a currency
  symbol or code next to a number (`$ € £ ₹`, `USD INR EUR GBP Rs`); dates (`\d{4}-\d{2}-\d{2}`, a month name
  followed by a 4-digit year, "in/since/by/until" followed by a year 1990-2099); licence ids (whole token,
  case-insensitive, `(?<![\w.-])id(?![\w.-])`) and phrases (case-insensitive substring).
- `validate(stack: dict, facts: list[dict], rules: dict, licences: dict) -> list[str]`: the errors, in this
  order: schema errors (stop here if any); every `subject` in `layers[].projects`, `layers[].services`,
  `accepted` and `cost.parts` is in the facts; every `github:` project has a fact for each field in
  `rules["required_fields"]` (a fact with `to_verify` counts as present); `prose_errors` on every `reason`,
  `alternative.why_not` and `risks` item, reported as `$.layers[0].reason: fact-shaped text "40k"`; every
  capability's `layer` names an existing layer; outcome `project` needs that layer's `projects` non-empty, and
  outcome `service` needs its `services` non-empty (each `price:` subject in the facts, a `to_verify` fact being
  enough in M1: real prices come in T19); `build-yourself` needs nothing.
- CLI: `python skills/stack-scout/scripts/validate.py STACK_JSON [--facts FILE]` (default: `facts_path(stack["facts_as_of"])`).
  Prints `{"ok": true}` (exit 0) or `{"ok": false, "errors": [...]}` (exit 2). A missing facts file is exit 2
  with that error.

**Steps**
1. Write `tests/test_validate.py`:
   - **Allowed prose** (no errors): "Python 3 with FastAPI", "OAuth 2.0 login", "serves HTTP/2", "files in S3",
     "runs on EC2", "meets ISO 27001", "Postgres 16 for storage", "Apache Kafka for events", "Apache Airflow
     schedules jobs", "commit history is clean".
   - **Rejected prose:** "40k stars", "over 12,000 stars", "350 contributors", "99.9% uptime", "costs $20 a
     month", "Rs 500 per month", "released 2024-03-01", "since March 2024", "in 2023", "MIT licensed", "under the
     Apache License", "uses Apache-2.0", "BUSL-1.1 since".
   - a capability with outcome `project` whose layer has no projects fails; one with outcome `service` and a
     `price:` subject backed only by a `to_verify` fact passes; a capability naming an unknown layer fails;
   - a stack whose project is missing from the facts fails with that subject named; one missing
     `latest_release` fails; one whose `latest_release` fact has `to_verify` passes; a schema error stops early.
   - CLI exit codes 0 and 2.
   Run `python -m unittest tests.test_validate -v`. Expect: `ModuleNotFoundError: No module named 'validate'`.
2. Write `skills/stack-scout/data/licences.json` and `skills/stack-scout/scripts/validate.py`. Run again. Expect: `OK`.
3. Full suite, commit `T8: validate`.

**Done check:** `python -m unittest tests.test_validate -v`. Expect: `OK`, all 23 prose cases plus at least 5
others.

**Watch out:** "MIT" must not match inside "commit" or "submit" (the whole-token rule). "ISO 27001" has no
unit, so no count rule catches it; keep it that way. Error messages name the JSON path, so the skill can fix the
exact field.

### T9 `render.py`: `stack.md` from `stack.json` and the facts file

Serves: R7, R9, R10. Depends on: T8. Size: M. Issue: <#>

**Files**
- Create: `skills/stack-scout/scripts/render.py`, `skills/stack-scout/templates/stack.md` (read through `ROOT/"templates"`). Test: `tests/test_render.py`, golden
  files `tests/fixtures/render/stack.json`, `facts.json`, `expected.md`.

**Tests that read these files:** `tests/test_validate.py` (imports `validate`; unchanged).

**Interfaces**
- `skills/stack-scout/templates/stack.md`: a `string.Template` with `$facts_as_of`, `$partial_note`,
  `$assumed`, `$layers`, `$capabilities`, `$risks`, `$cost`, `$to_verify`, `$accepted`; headings in this order:
  `# Tech stack`, `Facts as of`, `## Assumed answers`, `## Stack by layer`, `## Capabilities`, `## Risks`,
  `## Monthly cost`, `## To verify`, `## Accepted licence conflicts`.
- `render(stack: dict, facts: list[dict]) -> str`: runs `validate.validate` first and raises
  `ValueError(errors)` if it fails. Each layer: choice, reason, the alternative and why not, and a table
  `| Project | Stars | Licence | Last activity | Archived | Latest release |` where every value cell is a link to
  its fact's `source` (`[69687](https://github.com/expressjs/express)`), and a fact with `to_verify` renders as
  `to verify: <reason>`. Capabilities list the outcome in words ("open-source project", "managed service", "build
  it yourself"). Every `to_verify` fact **of a subject the stack references** (projects, services, accepted, cost parts) and
  every `unchecked` item appears under "To verify"; facts of dropped candidates do not; a `partial` stack
  starts with "Partial result: <n> checks not finished." Numbers print with no thousands separator.
- CLI: `python skills/stack-scout/scripts/render.py STACK_JSON [--facts FILE] [--out FILE]` (default out: `stack.md` next to the
  stack file). Prints `{"ok": true, "out": "<path>"}` or exit 2 with the validation errors.

**Steps**
1. Write the golden fixtures by hand (2 layers, 3 projects, 1 fact with `to_verify`, 1 assumed answer, 1
   build-yourself capability) and `expected.md`. Write `tests/test_render.py`: output equals `expected.md`
   exactly; every number in the projects table sits inside a link; an invalid stack raises; the CLI writes the
   file. Run `python -m unittest tests.test_render -v`. Expect: `ModuleNotFoundError: No module named 'render'`.
2. Write the template and `skills/stack-scout/scripts/render.py`. Run again. Expect: `OK`.
3. Full suite, commit `T9: render`.

**Done check:** `python -m unittest tests.test_render -v`. Expect: `OK`.

**Watch out:** compare with `\n` line endings on every platform (`newline="\n"` when writing). Escape `|` in
values inside table cells. The model never writes `stack.md` itself; this script is the only writer.

### T10 Starter question bank, the skill and the `/stack-scout` command

Serves: R2, R3, R4, R12, R14. Depends on: T2, T6, T7, T8, T9. Size: M. Issue: <#>

**Files**
- Create: `skills/stack-scout/SKILL.md`, `skills/stack-scout/questions.json`, `commands/stack-scout.md`.
- Change: `tests/check.py`. Test: the new checks in `tests/check.py`.

**Tests that read these files:** `tests/check.py`; `tests/test_schema.py` (the questions schema; unchanged).

**Interfaces**
- `questions.json` (passes `questions.schema.json`; each `default` is one of its `options`, checked in
  `tests/check.py`): the six starter questions, in rank order:
  1. `private_names`: "Which names must never leave this machine (client, product, project)?" options
     "None", "I'll type them"; default "None".
  2. `distribute`: "Will you distribute this product to others (sell, ship or host it for customers)?" options
     "Yes, we distribute it", "No, internal use only", "Not sure"; default "Not sure" (treated as yes for licence
     checks).
  3. `language`: "Which main language should the backend use?" options "Python", "TypeScript / Node", "Go",
     "Java / Kotlin"; default "Python".
  4. `cloud`: "Where will it run?" options "AWS", "Azure", "Google Cloud", "No preference"; default "No
     preference".
  5. `scale`: "How many users in the first year?" options "Under 100", "100 to 10,000", "Over 10,000"; default
     "100 to 10,000".
  6. `budget`: "Monthly running budget?" options "Free tiers only", "Under USD 100", "Under USD 1,000", "No fixed
     limit"; default "Under USD 100".
- `commands/stack-scout.md`: frontmatter `description` and `argument-hint: <sow-file> [--answers FILE]
  [--defaults] [--private-terms FILE]`; the body tells Claude to use the stack-scout skill with `$ARGUMENTS`.
- `SKILL.md`: frontmatter `name: stack-scout` and a `description` that says when to use it ("a statement of
  work, a problem statement or a project brief, and the user wants a tech stack"). The body, in this order:
  1. **Where the scripts are:** `SS` is this skill's own folder, the "Base directory for this skill" Claude Code
     shows when the skill loads, written with forward slashes; every script call is
     `python "$SS/scripts/<name>.py" ...`. Run every script with the user's project folder as the working
     directory, so `.stack-scout/` lands there.
  2. **Read the SOW** (M1: `.md` and `.txt` with the Read tool; other formats arrive in T13).
  3. `guard.py terms --sow <file> [--private-terms F] [--answers F]`, again after the interview.
  4. **Open points:** for each bank question, decide whether the SOW already answers it; ask only the open
     ones, in rank order, at most 4 per question screen and 8 in all. On screen the **default is always the
     first option**, labelled `<default> (Recommended; pick this if unsure)`, which is the "use the default"
     path; the other options follow in bank order (at most 4 options in all; the screen adds "Other" itself).
     With `--defaults` or `--answers`, ask nothing; record defaults as assumed. Write every answer to
     `.stack-scout/answers.json` (`{"<id>": "<answer>"}`), then run `guard.py terms` again with
     `--answers .stack-scout/answers.json`. **The `private_names` answer is never copied into `stack.json` or
     `stack.md`:** its `assumed` entry, if any, reads "(kept private)".
  5. **Capabilities:** generic names only (no client or product terms), each with its layer.
  6. **Candidates:** for each capability, 2-4 well-known open-source projects; run `guard.py check` on any web
     search before making it; `facts.py verify` every candidate in one call.
  7. **Choose:** drop `exists = false`, `archived = true`, and `last_activity` older than `dead_after_months`
     in `skills/stack-scout/data/rules.json`. A candidate whose `last_activity` is "to verify" (bot-only history) is **kept but
     never preferred**: choose it only when no candidate has a confirmed recent `last_activity`, and then name
     the risk in `risks`; it also shows under "To verify". A capability left with no candidate gets outcome
     `build-yourself`, or `service` with a `price:<service>` subject recorded by
     `facts.py to-verify price:<service> price "pricing not checked yet" --source <official pricing page>`.
  8. **Write `stack.json`** (schema in `$SS/schema/stack.schema.json`): references only, prose with no
     fact-shaped text and no licence names.
  9. `validate.py stack.json`; on errors fix the named field and validate again, at most 3 times, then mark the
     item unchecked. Never write `stack.md` by hand: `render.py stack.json`.
  10. **Report:** the path to `stack.md`, the to-verify list, and the suggestion to add `.stack-scout/` to
      `.gitignore`.
  11. **Never:** state a fact not in the facts file; send a search not passed by `guard.py`; go past about 200
      tool calls (stop with a partial, validated result).
- New checks in `tests/check.py` (each a numbered check, so the `ok:` count grows): the skill frontmatter has `name` and `description`; the body mentions
  `guard.py terms`, `guard.py check`, `facts.py verify`, `validate.py` and `render.py`; the command file has
  `description` and `argument-hint`; `questions.json` passes its schema and every default is an option; every
  `python "$SS/scripts/X.py"` the skill names exists in `skills/stack-scout/scripts/`.

**Steps**
1. Add the checks to `tests/check.py`. Run `python tests/check.py`. Expect: `FAIL:` lines for the missing skill,
   command and bank, exit 1.
2. Write `questions.json`, `commands/stack-scout.md` and `SKILL.md`. Run again. Expect: `ok: <n> checks`.
3. Full suite, commit `T10: question bank, skill and command`.

**Done check:** `python tests/check.py`. Expect: `ok:` and exit 0.

**Also, a model call:** the skill is model behaviour; its eval cases come in T28-T30, and its first real run is
T12's done check. The guardrails in code are `validate.py` (T8) and `guard.py` (T6), already tested.

**Watch out:** the question screen allows at most 4 questions and 2-4 options each; the default shown first is
one of the question's own options, so a bank question may have up to 4 options and all of them fit. Bank option
lists are **not** in display order: the skill moves the default to the front (for `cloud`, "No preference"
comes first on screen). No Windows backslashes in the skill's commands. If the question tool is missing, ask the
same questions as a numbered text list.

### T11 Installers and their CI test

Serves: R11. Depends on: T10. Size: M. Issue: <#>

**Files**
- Create: `install.sh`, `install.ps1`. Test: `tests/test_install.py` (reads T9's fixtures in
  `tests/fixtures/render/`).
- Change: `tests/check.py` (installer checks), `.github/workflows/check.yml` only if a step is needed.

**Tests that read these files:** `tests/test_repo.py` (reads `check.yml`), `tests/check.py`.

**Interfaces**
- `./install.sh [--uninstall]` and `install.ps1 [--uninstall]`, modelled on `idea-to-orbit/install.sh` and
  `install.ps1` (same config folder rule, `$CLAUDE_CONFIG_DIR` else `~/.claude`; same marker idea), but **no
  hook and no settings.json change**. Install copies `skills/stack-scout/` (with its `scripts/`, `data/`,
  `schema/`, `templates/` and `questions.json`, without `__pycache__/`) to `<config>/skills/stack-scout/`
  (marker file `.stack-scout` inside) and `commands/stack-scout.md` to `<config>/commands/stack-scout.md`.
  Nothing else. It stops before changing anything if a
  `<config>/skills/stack-scout/` without the marker exists (someone else's). Uninstall removes exactly those.
  Both print one line per action and end with `Installed Stack Scout <version>` or `Removed Stack Scout`.
- PowerShell 5.1 reads `--uninstall` from `$args` (it does not bind to a named parameter).

**Steps**
1. Write `tests/test_install.py`: with `CLAUDE_CONFIG_DIR` set to a temp folder, run the installer for the
   platform (`bash install.sh` everywhere, with bash found by a `find_bash()` helper copied from
   `idea-to-orbit/tests/check.py`, because on Windows a bare `bash` from `subprocess` can resolve to WSL's
   `System32/bash.exe`; also `powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1` on Windows), check
   every file is in place, that `python <config>/skills/stack-scout/scripts/schema.py questions
   <config>/skills/stack-scout/questions.json` exits 0, and that `python
   <config>/skills/stack-scout/scripts/render.py` on T9's golden fixtures writes the expected file (the copied
   scripts find their data and template); run again (rerun is
   safe); `--uninstall` leaves the temp folder with no Stack Scout files; a foreign `skills/stack-scout/` without
   the marker makes install exit 1 and change nothing. Run `python -m unittest tests.test_install -v`. Expect:
   failures, installer not found.
2. Write `install.sh`, then `install.ps1`. Run `git update-index --chmod=+x install.sh` so `./install.sh`
   runs on macOS and Linux. Run the test again. Expect: `OK` (on Windows both installers ran).
3. Full suite, commit `T11: installers`, push, open the pull request.

**Done check:** `gh pr checks`. Expect: all 6 matrix jobs `pass`, including `test_install` on Windows and macOS.

**Also, a CI change:** if `check.yml` changes, extend `tests/test_repo.py` to fail when the change is undone.

**Watch out:** `set -e` with `[ -f x ] && rm x` stops the script when the test is false; use `if`. macOS has bash
3.2: no associative arrays, no `${var,,}`. Copy with `cp -R`, not `rsync`.

### T12 End to end: live smoke and one real skill run

Serves: R1, R5, R7. Depends on: T11, T3. Size: S. Issue: <#>

**Files**
- Create: `tests/smoke_live.py`. Change: `docs/orbit/JOURNAL.md` (the result); and, for each guess the fresh
  agent reports, `skills/stack-scout/SKILL.md` with its check in `tests/check.py`; if a real API answer differs
  from the mock, `tests/mock_api.py` routes in `tests/test_facts_verify.py` first, then
  `skills/stack-scout/scripts/facts.py`.

**Tests that read these files:** none (not part of the fast tests: its name does not start with `test_`).

**Interfaces**
- `python tests/smoke_live.py`: needs a token (`get_token()`); without one prints `skip: no GitHub token` and
  exits 0. With one, in a temp `STACK_SCOUT_DIR`: `facts.py verify expressjs/express fastapi/fastapi
  request/request` against the real API; checks `express` and `fastapi` have every required field and
  `request/request` has `archived = true`; writes a fixed small `stack.json` using `express`; runs
  `validate.py` and `render.py`; prints `ok` and the GraphQL points used.

**Steps**
1. Write `tests/smoke_live.py`. Run `python tests/smoke_live.py`. Expect: `ok` and a points count (fix the
   scripts, not the smoke, if a real API answer differs from the mock: add that shape to the mock tests first).
2. Install with `bash install.sh`. A **fresh agent** that has not seen this work reads
   `<config>/skills/stack-scout/SKILL.md` and follows it on `tests/fixtures/sows/01-memo-generator.md` with
   `--defaults`, in a temp folder.
3. Check the run: `python <config>/skills/stack-scout/scripts/validate.py stack.json` exits 0; `stack.md` exists, has
   every heading of the template, and every number in its projects tables is a link.
4. **One plugin install too:** in Claude Code, `/plugin marketplace add <repo path>` then
   `/plugin install stack-scout@stack-scout`, and confirm the skill finds `SS` from its base directory (one
   `guard.py terms` call is enough). Where `/plugin` is not available (the VS Code extension has had no
   `/plugin`), record that in `JOURNAL.md` and move this check to T36; do not skip it silently.
5. Write the result (points used, tool calls, time, anything the agent had to guess) in `JOURNAL.md`; each
   guess becomes a fix to `SKILL.md` with its check in `tests/check.py`.
6. Commit `T12: walking skeleton end to end`.

**Done check:** `python tests/smoke_live.py` prints `ok`; `validate.py` on the fresh agent's `stack.json` prints
`{"ok": true}`.

**Watch out:** `request/request` is used because it is archived; confirm that in step 1's output, and pick
another archived repository (and update this card) if it ever is not. Use the owner's `gh` login, never a token
pasted in chat.

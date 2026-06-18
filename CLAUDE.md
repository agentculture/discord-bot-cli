# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`discord-bot-cli` is an AgentCulture mesh agent whose stated domain is *"giving
an agent Discord access via a bot."* It started life as the
**culture-agent-template** scaffold — a generic, dependency-free **agent-first
introspection CLI** (the `afi-cli` pattern, cited from
[teken](https://github.com/agentculture/teken)) plus a mesh identity and a
vendored skill kit — and the **first Discord increment now ships on top of it**:
one-shot `channel` / `message` / `thread` / `user` verbs over `discord.py`. The
introspection scaffold is still the substrate; the Discord verbs are the first
domain layer built on it (see *Architecture → Discord domain* below).

## Commands

No `.venv` exists on a fresh checkout — start with `uv sync`.

```bash
uv sync                              # create the env (uv sync --all-extras --dev in CI)
uv run pytest -n auto                # full suite, parallel (pytest-xdist) — 30 tests today
uv run pytest tests/test_cli.py::test_whoami_json   # a single test
uv run pytest -k explain            # tests matching an expression
uv run pytest -n auto --cov=discord_bot_cli --cov-report=term   # coverage (report fail_under=60)
```

Lint/format — the CI `lint` job runs all of these and **fails on any**:

```bash
uv run black --check discord_bot_cli tests
uv run isort --check-only discord_bot_cli tests
uv run flake8 discord_bot_cli tests
uv run bandit -c pyproject.toml -r discord_bot_cli
uv run teken cli doctor . --strict   # the agent-first rubric gate (the "afi rubric gate" step)
```

Auto-fix formatting: `uv run black discord_bot_cli tests && uv run isort discord_bot_cli tests`.
Line length is **100** everywhere (black, isort `black` profile, flake8 `max-line-length`).
Markdown is linted in CI with `markdownlint-cli2` (config `.markdownlint-cli2.yaml`;
`.claude/skills/**` is excluded).

### Running the CLI

`[project.scripts]` installs **two** console scripts, both pointing at
`discord_bot_cli.cli:main`: `discord` and `discord-bot-cli`. So all of these
work:

```bash
uv run discord whoami                    # short form
uv run discord-bot-cli whoami            # dist-name form (matches the docs)
uv run python -m discord_bot_cli learn   # module entry point
```

The README quickstart and the in-CLI help/`explain` strings use
`discord-bot-cli`; the `discord` alias is the ergonomic short command. The
package dir is `discord_bot_cli`, the dist/PyPI name is `discord-bot-cli`.

## Architecture

Two layers. The split is deliberate: failures route through one error path, and
output never mixes streams.

**`discord_bot_cli/cli/` — argparse front end + dispatch:**

- `__init__.py:main(argv) -> int` builds the parser, parses, and dispatches.
  `_CliArgumentParser` subclasses `argparse.ArgumentParser` and overrides
  `.error()` so **parse-time** errors (unknown verb, bad flag) render as the
  structured `error:` / `hint:` contract and exit **1**, not argparse's default
  stderr + exit 2. Because the JSON flag isn't parsed yet at that point, `main`
  pre-scans raw argv for `--json` and stashes it in the class-level `_json_hint`.
- `_dispatch()` calls the selected handler, catches `CliError` → its exit code,
  and wraps **any** other exception into a `CliError` so no Python traceback ever
  leaks to stderr.
- `_errors.py` — `CliError(code, message, remediation)` dataclass-exception and
  the exit-code constants. **Exit contract:** `0` ok · `1` user error · `2`
  environment error · `3+` reserved.
- `_output.py` — `emit_result` (→ stdout), `emit_error` (→ stderr, as
  `error:` + `hint:` lines), `emit_diagnostic` (→ stderr). The `hint:` prefix is
  required by the agent-first rubric. **Rule: results to stdout, everything else
  to stderr, never mixed; `--json` toggles structured payloads on the same
  streams.** Handlers call these helpers directly with a `json_mode=` kwarg.
- `_commands/` — one module per verb/noun: `whoami`, `learn`, `explain`,
  `overview`, `doctor`, and the `cli` noun group. Each exports
  `register(sub)` (calls `sub.add_parser(...)` and `p.set_defaults(func=...)`)
  and a `cmd_*(args: argparse.Namespace) -> int` handler. Registration is
  explicit: `_build_parser()` imports each module and calls its `register(sub)`
  (there is **no** auto-discovery registry).

**`discord_bot_cli/explain/` — the addressable doc catalog:**

- `catalog.py:ENTRIES` maps command-path **tuples** (e.g. `("cli","overview")`,
  `()` and `("discord-bot-cli",)` both → root) to verbatim Markdown strings.
- `__init__.py:resolve(path)` looks a tuple up (raising `CliError` with a hint on
  a miss); `known_paths()` lists them. `explain` is a **global** verb, not nested
  under a noun.

**Where identity comes from:** `_commands/whoami.py` is the single reader of
`culture.yaml`. `find_culture_yaml()` walks up from the module's `__file__`
(deliberately *not* the cwd, so the identity is always this agent's own).
`read_agent_fields()` hand-parses the first agent block's `suffix`/`backend`/
`model` — **no PyYAML**, to keep runtime deps empty — and `report()` returns
`{nick, version, backend, model}` (missing fields fall back to `"unknown"`;
nick falls back to `discord-bot-cli`). `overview.py` and `doctor.py` both import
from `whoami.py`, and `cli.py`'s `cli overview` reuses `overview.py`'s section
helpers — so the introspection verbs can't drift from `whoami`.

`doctor.py` mirrors the `steward doctor` invariants: `prompt_file_present` +
`backend_consistency` (`_PROMPT_FILE`: `claude`→`CLAUDE.md`, `acp`→`AGENTS.md`,
`gemini`→`GEMINI.md`) plus `skills_present`. Exit 1 when unhealthy; from a wheel
install with no `culture.yaml` it emits one info check and exits 0.

**Discord domain — `discord_bot_cli/discord_client.py` (the transport seam):**

The single place that talks to `discord.py`. Every Discord verb routes through
`run(action)`, which: reads the bot token from `$DISCORD_BOT_TOKEN` via
`require_token()` (env only, never a flag → `EXIT_ENV_ERROR(2)` if unset),
**lazy-imports** `discord` via `require_discord()` (so the runtime stays
`dependencies = []`; absent extra → `EXIT_ENV_ERROR(2)` + install hint, never an
`ImportError` traceback), then `asyncio.run`s a one-shot session — `login` →
`await action(client)` → **always `close()`** in a `finally` (no daemon, no
gateway subscription; `Intents.none()`). `discord.py`'s `LoginFailure` /
`Forbidden` / `NotFound` / `HTTPException` / `DiscordException` are mapped to
`CliError` so nothing leaks. `parse_id()` turns a bad snowflake into a
`EXIT_USER_ERROR(1)` with a hint. **This is the seam the tests stub** — patch
`discord_client.run` to feed a recording fake client (`tests/conftest.py`); no
live token or network is ever needed.

The verbs live in `_commands/{channel,message,thread,user}.py` (nouns matching
Discord REST resources; `_discord_common.py` holds the shared `overview`
renderer + `--json` helper). Each `cmd_*` builds an `async def action(client)`
coroutine and calls `discord_client.run(action)`. `discord.py` is the optional
`[discord]` extra in `pyproject.toml` (also in the dev group so CI exercises the
code paths). `post` / `reply` / `thread create` return the created id in `--json`
so output composes into the next verb.

### Adding a command

1. Create `discord_bot_cli/cli/_commands/<verb>.py` with `cmd_<verb>(args) -> int`
   and a `register(sub)`.
2. Import it and call `_<verb>.register(sub)` in `cli/__init__.py:_build_parser()`.
3. Add a Markdown entry (keyed by its path tuple) to `explain/catalog.py:ENTRIES`
   — `test_every_catalog_path_resolves` and the rubric expect every path to
   resolve.
4. Surface it where the command lists are **hand-maintained**: `learn.py`
   (`_TEXT` *and* `_as_json_payload`) and `overview.py` (`_VERBS`). These lists
   are not generated from the catalog, so they must be updated by hand.

## Hard constraints

- **Zero runtime dependencies.** `pyproject.toml` has `dependencies = []` on
  purpose (hence the hand-rolled YAML scanner). Keep the *runtime* package
  dependency-free; third-party packages go in the `dev` group, or — for a domain
  capability — under `[project.optional-dependencies]` and **lazy-imported inside
  the handler** (the sanctioned pattern: `discord.py` under the `discord` extra,
  imported in `discord_client.require_discord()`, never at module top level).
  `tests/test_no_runtime_deps.py` enforces both halves: `dependencies == []` and
  no top-level third-party import anywhere in the package. Adding a *hard* runtime
  dep is a real architectural decision. `__version__`
  (`discord_bot_cli/__init__.py`) is read from installed package metadata via
  `importlib.metadata`, so the single version source is `pyproject.toml` — after
  a bump, re-run `uv sync` for `whoami`/`overview` to report the new number.
- **Python ≥ 3.12**, uv-managed, hatchling build, package at the repo top level
  (no `src/` wrapper).

## Workflow & CI

- **Bump the version on every PR** (`version-bump` skill: patch/minor/major;
  prepends a Keep a Changelog entry). The `version-check` CI job **fails the PR**
  if `pyproject.toml`'s version equals `main`'s — even for docs/config/CI-only
  changes.
- PRs go through the **`cicd` skill** (`status` = SonarCloud quality gate +
  hotspots + unresolved threads; `await` blocks on them). It delegates the PR
  lifecycle to `devex pr` (needs `devex` ≥ 0.21 on PATH); `communicate` wraps
  `agtag` for cross-repo issues. `run-tests`, `sonarclaude`, and `version-bump`
  skills are also wired for this repo.
- `.github/workflows/tests.yml`: `test` (pytest + coverage, then SonarCloud only
  when `SONAR_TOKEN` is set — fork PRs and token-less repos skip it and stay
  green), `lint`, and `version-check`.
- `.github/workflows/publish.yml`: PRs from the same repo publish a
  `.dev<run>` build to **TestPyPI**; pushes to `main` publish to **PyPI** — both
  via **Trusted Publishing** (OIDC, no API token).

## Skills are vendored (cite-don't-import)

Everything under `.claude/skills/` is copied from upstream (**guildmaster**, the
skills supplier; three skills — `think`, `spec-to-plan`, `assign-to-workforce` —
originate in **devague** and are re-broadcast). **Don't edit the vendored
copies** — re-sync from the source. Every `SKILL.md` must keep `type: command` in
its frontmatter (load-bearing: the culture/claude backend's `core.skill_loader`
silently skips skills without it). See [`docs/skill-sources.md`](docs/skill-sources.md)
for per-skill provenance, the re-sync procedure, and the logged in-place `agex→devex`
divergence.

## Renaming the agent

The strings `discord_bot_cli` (package), `discord-bot-cli` (dist), and `discord`
(script) are hard-coded in ~100 places across `pyproject.toml`, the package,
`tests/`, `sonar-project.properties`, and the docs. To fork this template,
`git grep` every occurrence first, then update `culture.yaml`
(`suffix`/`backend`) and rewrite this `CLAUDE.md`.

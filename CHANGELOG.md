# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-06-24

### Added

- **Memory-discipline "Conventions and workflow" section in `CLAUDE.md`** — a
  per-task *recall-before / remember-after* convention (scope localized to this
  repo's nick) so the vendored `remember` / `recall` skills are actually used,
  not just present: `/recall` before non-trivial work to build on prior
  decisions instead of re-deriving them, and `/remember` when a non-obvious
  decision, constraint, fix-and-why, or hard-won gotcha surfaces. The section
  documents this repo's memory as **in-repo and public** — records resolve to
  `<repo-root>/.eidetic/memory` (committed, team- and mesh-shared). Inserted
  idempotently (skipped if already present), slotted under an existing
  "Conventions and workflow" heading when one exists, else appended.

### Changed

- **Refreshed the `remember` + `recall` wrappers from eidetic-cli 0.10.0**
  (cite-don't-import) — picks up eidetic's **project-local store default**: the
  files backend now resolves per record by visibility — PUBLIC records inside a
  git repo go to `<repo-root>/.eidetic/memory` (committed, team-shared), PRIVATE
  records (or any record outside a repo) go to `$HOME/.eidetic/memory` (never
  committed), an explicit `EIDETIC_DATA_DIR` still wins, and recall reads both
  stores and merges. Also carries the 0.9.3 hardening (interactive-stdin guard,
  `help` as a search term, SIGPIPE-safe suffix parsing). **Recipe policy
  override (the wrappers here are NOT byte-verbatim):** the injected default
  visibility is flipped from eidetic's `private` to **`public`**, so a plain
  `/remember` lands the note in `./.eidetic/memory` in this repo, kept as part
  of the repo — pass `--visibility private` to route a record to `$HOME`
  instead. `remember` drives `eidetic remember` (idempotent upsert of one JSON
  record or an NDJSON batch on stdin); `recall` drives `eidetic recall` with
  four search modes (exact / approximate / keyword / hybrid). Each `SKILL.md` is
  localized only in the illustrative `--scope <nick>` examples (Provenance keeps
  "First-party to eidetic-cli"). Runtime dep: the `eidetic` CLI on PATH (else a
  local eidetic-cli checkout with `uv`) — **`eidetic >= 0.10.0`** for the
  in-repo routing; on an older CLI the public records still work but are stored
  in `$HOME/.eidetic/memory` instead of in-repo. Propagated by rollout-cli's
  `eidetic-memory` recipe.

## [0.4.0] - 2026-06-23

### Added

- **Vendored the `remember` + `recall` memory skills from eidetic-cli**
  (cite-don't-import) — the write/read halves of eidetic's shared
  `~/.eidetic/memory` surface, so this agent (Claude and its colleague backend)
  can persist facts across sessions and recall them later, sharing one store.
  `remember` drives `eidetic remember` (idempotent upsert of one JSON record or
  an NDJSON batch on stdin, dedup by id + content hash); `recall` drives
  `eidetic recall` with four search modes — exact / approximate / keyword /
  hybrid — each hit carrying text, full provenance metadata, a relevance score,
  and a freshness signal. The `.sh` wrappers are byte-verbatim from eidetic-cli
  (their first-party origin); each `SKILL.md` is localized only in the
  illustrative `--scope <nick>` examples (Provenance keeps "First-party to
  eidetic-cli"). Both default to this agent's PRIVATE scope, reading the suffix
  from `culture.yaml`. Runtime dep: the `eidetic` CLI on PATH (else a local
  eidetic-cli checkout with `uv`). Propagated by rollout-cli's `eidetic-memory`
  recipe.

## [0.3.0] - 2026-06-19

### Added

- tests/test_live_discord.py: opt-in live tests that drive the real Discord API (the `live` pytest marker). Doubly gated — they self-skip unless `DISCORD_LIVE_TESTS=1` and `DISCORD_BOT_TOKEN` are both set — so a routine `pytest` never logs in or posts even with a token in the env. Covers reads (user/channel list/channel messages), the full write chain (post → reply → react → thread create → thread post, composing on each returned id, posting to a sandbox channel), and the live exit-1 error mapping
- .github/workflows/live-tests.yml: a dedicated CI lane for the live tests on `workflow_dispatch` + push to `main`. No-ops on forks / token-less repos (gated on `env.DISCORD_BOT_TOKEN != ''`); reads the bot token from the `DISCORD_BOT_TOKEN` secret and the guild/channel/user ids from repository variables (defaulting to the experiments sandbox)
- `live` pytest marker registered in pyproject.toml

## [0.2.0] - 2026-06-18

### Added

- Discord domain verbs over discord.py (optional [discord] extra): channel list/messages, message post/reply/react, thread create/post, user get — each one-shot, agent-first, with --json
- discord_bot_cli/discord_client.py transport seam: DISCORD_BOT_TOKEN auth, lazy discord.py import, async one-shot run() that always closes the client, and discord exception->CliError mapping
- tests/test_no_runtime_deps.py guard asserting dependencies==[] and no top-level third-party imports

### Changed

- overview/learn/explain now surface the Discord verbs; explain catalog gains channel/message/thread/user entries
- markdownlint ignores devague specs/plans/.devague artifacts and .venv; CI markdownlint glob updated to match
- SonarCloud triage: `discord_client.run`/`_run_async` use PEP 695 generic syntax (`def run[T](...)`) instead of a module-level `TypeVar`; the duplicated "Numeric channel id." argparse help in `message.py` is a single `_CHANNEL_ID_HELP` constant

## [0.1.5] - 2026-06-18

### Changed

- **Re-vendored the `ask-colleague` skill wrapper from its canonical colleague
  source** (`.claude/skills/ask-colleague/scripts/ask-colleague.sh`): the wrapper
  now drives the `colleague flight` pilot verbs — `monitor` / `guide` / `stop`
  plus the `--watch` flag that arms a drive (`explore` / `review` / `write`) so it
  can be watched, guided mid-flight, and cooperatively stopped. This supersedes the
  earlier colleague#186 snapshot (which predated flights). It keeps the `--json`
  machine-readable output added then — stdout carries **only** the result JSON (the
  drive verbs emit the normalized `TaskResult`; `feedback` / `clean` forward
  `--json` to colleague) while every diagnostic/digest line goes to stderr. The
  bundled `SKILL.md` template documents the new verbs/flag; an existing downstream
  `SKILL.md` is left untouched (it carries a repo-specific provenance token and
  may diverge). Where the skill was absent, it is added fresh (wrapper +
  `SKILL.md` + prompts).

## [0.1.4] - 2026-05-31

### Changed

- Replaced the bootstrap seed `CLAUDE.md` with a tailored runtime prompt for the agent (the `/init` pass): documents the uv/pytest/lint commands and the agent-first rubric gate, the two-layer architecture (the `cli/` argparse dispatcher with the structured `error:`/`hint:` contract and the `explain/` path-tuple catalog), where identity is resolved (`_commands/whoami.py` reads `culture.yaml` with no PyYAML), the zero-runtime-dependency constraint, and the version-bump-every-PR / `cicd` PR workflow. Flags that the installed console script is `discord` (not `discord-bot-cli`, which the README/help strings still reference).

### Fixed

- Added a `discord-bot-cli` console-script alias to `[project.scripts]` (alongside `discord`) so `uv run discord-bot-cli ...` works, matching the README quickstart, the `explain` catalog, argparse `prog`, and the in-CLI help strings. Resolves the Qodo PR #1 "CLI name mismatch" review — both `discord` and `discord-bot-cli` now invoke `discord_bot_cli.cli:main`.
- Added a `("discord",)` key to the `explain` catalog (`discord_bot_cli/explain/catalog.py`) so `discord explain discord` resolves to the root entry. The console script is `discord` while the catalog's self-key was `discord-bot-cli`, so the agent-first rubric's `explain_self` check (`teken cli doctor . --strict`, the CI `lint` gate) ran `explain discord` and failed — a latent scaffold mismatch between `[project.scripts]` and the catalog.

## [0.1.3] - 2026-05-31

### Changed

- Expanded the clone-and-rename instructions in `CLAUDE.md`: added `README.md` to
  the rename targets and a portable `git grep` discovery command so a cloner can
  find every occurrence of the template name (hard-coded in ~100 places across the
  package, including the CLI command files and `_ISSUES_URL` in
  `discord_bot_cli/cli/__init__.py`) rather than renaming by hand.
- Synced `README.md`'s "Make it your own" checklist with `CLAUDE.md`: it now lists
  `README.md` itself as a rename target and points to `CLAUDE.md`'s discovery
  command as the authoritative procedure, so the two onboarding checklists no
  longer drift.

## [0.1.2] - 2026-05-30

### Changed

- Renamed the PR-lifecycle CLI references `agex` / `agex-cli` to `devex` (same
  tool, new name) across `CLAUDE.md`, `docs/skill-sources.md`, `.gitignore`, and
  the vendored `cicd`, `assign-to-workforce`, and `communicate` skills — the
  `cicd` scripts now invoke `devex pr`.
- Logged the vendored-skill in-place patch as a local divergence in
  `docs/skill-sources.md`; the matching canonical rename is tracked upstream for
  guildmaster in
  [agentculture/guildmaster#48](https://github.com/agentculture/guildmaster/issues/48)
  so a future re-sync reconciles cleanly.
- Aligned the documented `devex` version floor to `>=0.21` across the vendored
  `cicd` `SKILL.md` and `workflow.sh` install hint (were `>=0.1`), matching
  `docs/skill-sources.md` and the `await`-era feature set; flagged upstream on
  guildmaster#48.

### Fixed

- SonarCloud now reports code coverage — added `relative_files = true` to
  `[tool.coverage.run]` so `coverage.xml` emits repo-relative paths that map to
  `sonar.sources=discord_bot_cli` (absolute / `.venv` paths were dropped
  as unmappable). Mirrors the sibling `convertible` setup.

## [0.1.1] - 2026-05-26

### Changed

- **CI gates on the SonarCloud quality gate**
  ([issue #3](https://github.com/agentculture/discord-bot-cli/issues/3)) —
  added `sonar.qualitygate.wait=true` to `sonar-project.properties` so a failing
  gate fails the `test` job when `SONAR_TOKEN` is set. Token-less repos and fork
  PRs remain green (the scan step is guarded by `if: env.SONAR_TOKEN != ''`).

## [0.1.0] - 2026-05-26

### Added

- **Onboarded into the AgentCulture mesh** ([issue #1](https://github.com/agentculture/discord-bot-cli/issues/1)).
- **Agent-first CLI** cited from teken's (`afi-cli`) `python-cli` reference
  (`teken cli cite`) — verbs `whoami`, `learn`, `explain`, `overview`, `doctor`,
  and the `cli` noun group. Runtime is self-contained (`dependencies = []`);
  `teken>=0.8` is a dev dependency only. Passes the seven-bundle agent-first
  rubric (`teken cli doctor . --strict`). `doctor` checks the agent-identity
  invariants (prompt-file-present, backend-consistency, skills-present).
- **Mesh identity**: `culture.yaml` (`suffix: discord-bot-cli`,
  `backend: claude`) and the matching `CLAUDE.md` prompt file.
- **Canonical guildmaster skill kit** (11 skills) vendored under
  `.claude/skills/` (cite-don't-import): `agent-config`, `assign-to-workforce`,
  `cicd`, `communicate`, `doc-test-alignment`, `pypi-maintainer`, `run-tests`,
  `sonarclaude`, `spec-to-plan`, `think`, `version-bump`. Every `SKILL.md`
  carries `type: command` (load-bearing for the culture/claude backend);
  `cicd` / `communicate` consumer-identifying prose adapted, all script bodies
  verbatim. Provenance in `docs/skill-sources.md`. Three skills (`think`,
  `spec-to-plan`, `assign-to-workforce`) originate in `devague`, re-broadcast
  via guildmaster.
- **Build + deploy baseline**: `pyproject.toml` (hatchling), `tests/` (pytest,
  xdist, coverage), `.github/workflows/{tests,publish}.yml` (CI rubric/lint gate,
  PyPI Trusted Publishing), `.flake8`, `.markdownlint-cli2.yaml`,
  `sonar-project.properties`, and `.claude/skills.local.yaml.example`.

### Changed

### Fixed

# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.5] - 2026-05-31

### Added

- Vendored the canonical `outsource` skill (explore/review/write) from guildmaster. Hands a scoped repo task to convertible (a different engine/mind) for a diverse second opinion; resolves the convertible CLI from PATH. Cite-don't-import copy; INBOUND_ORIGINS=guildmaster.

### Changed

### Fixed

- `outsource` skill (`scripts/outsource.sh`), patched in place over the vendored copy as a logged divergence (upstream [convertible#63](https://github.com/agentculture/convertible/issues/63)): user/parse-time errors now exit `1` (environment errors `2`) per the afi exit contract; every `error:` carries a `hint:`; `render_prompt` replaces `$BASE` before `$ARGUMENTS` so a literal `$BASE` in user text is no longer corrupted; worktree cleanup only deletes a `convertible/*` branch this run created. Refreshed `uv.lock` to 0.1.5; corrected the skill-kit count (11 → 12) and added the `outsource` provenance row in `docs/skill-sources.md`. Addresses Qodo review on PR#2.

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

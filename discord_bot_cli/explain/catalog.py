"""Markdown catalog for ``discord-bot-cli explain <path>``.

Each entry is verbatim markdown. Keys are command-path tuples. The empty tuple,
``("discord-bot-cli",)`` (dist name), and ``("discord",)`` (console script) all
resolve to the root entry.

Keep bodies self-contained: an agent reading one entry should get enough
context without chaining reads.
"""

from __future__ import annotations

_ROOT = """\
# discord-bot-cli

A clonable template for AgentCulture mesh agents. It carries an agent-first CLI
(cited from the teken `python-cli` reference), a mesh identity (`culture.yaml` +
`CLAUDE.md`), the canonical guildmaster skill kit under `.claude/skills/`, and a
buildable/deployable package baseline. Clone it, rename the package, edit
`culture.yaml`, and you have a new agent.

## Verbs

- `discord-bot-cli whoami` — identity probe from `culture.yaml`.
- `discord-bot-cli learn` — structured self-teaching prompt.
- `discord-bot-cli explain <path>` — markdown docs for any noun/verb.
- `discord-bot-cli overview` — descriptive snapshot of the agent.
- `discord-bot-cli doctor` — check the agent-identity invariants.
- `discord-bot-cli cli overview` — describe the CLI surface.

## Exit-code policy

- `0` success
- `1` user-input error
- `2` environment / setup error
- `3+` reserved

## See also

- `discord-bot-cli explain whoami`
- `discord-bot-cli explain doctor`
"""

_WHOAMI = """\
# discord-bot-cli whoami

Reports the agent's identity from `culture.yaml`: nick (`suffix`), backend,
served model, and the package version. Read-only.

## Usage

    discord-bot-cli whoami
    discord-bot-cli whoami --json
"""

_LEARN = """\
# discord-bot-cli learn

Prints a structured self-teaching prompt covering purpose, command map,
exit-code policy, `--json` support, and the `explain` pointer.

## Usage

    discord-bot-cli learn
    discord-bot-cli learn --json
"""

_EXPLAIN = """\
# discord-bot-cli explain <path>

Prints markdown documentation for any noun/verb path. Unlike `--help` (terse,
positional), `explain` is global and addressable by path.

## Usage

    discord-bot-cli explain discord-bot-cli
    discord-bot-cli explain whoami
    discord-bot-cli explain --json <path>
"""

_OVERVIEW = """\
# discord-bot-cli overview

Read-only descriptive snapshot of the agent: identity (from `culture.yaml`), the
verb surface, and the sibling-pattern artifacts the template carries. Accepts an
ignored `target` so a stray path never hard-fails.

## Usage

    discord-bot-cli overview
    discord-bot-cli overview --json
"""

_DOCTOR = """\
# discord-bot-cli doctor

Checks the agent-identity invariants `steward doctor` verifies:
prompt-file-present and backend-consistency (`claude` → `CLAUDE.md`), plus a
skills-present check. Exits 1 when unhealthy.

## Usage

    discord-bot-cli doctor
    discord-bot-cli doctor --json
"""

_CLI = """\
# discord-bot-cli cli

Noun group for CLI-surface introspection. `cli overview` describes the CLI
itself (distinct from the global `overview`, which describes the agent).

## Usage

    discord-bot-cli cli overview
    discord-bot-cli cli overview --json
"""


ENTRIES: dict[tuple[str, ...], str] = {
    (): _ROOT,
    ("discord-bot-cli",): _ROOT,
    # The installed console script is ``discord`` (see ``[project.scripts]``),
    # so ``discord explain discord`` resolves to the root entry too. Keeps the
    # agent-first rubric's ``explain_self`` check (``explain <script-name>``)
    # green alongside the ``discord-bot-cli`` dist-name key above.
    ("discord",): _ROOT,
    ("whoami",): _WHOAMI,
    ("learn",): _LEARN,
    ("explain",): _EXPLAIN,
    ("overview",): _OVERVIEW,
    ("doctor",): _DOCTOR,
    ("cli",): _CLI,
    ("cli", "overview"): _CLI,
}

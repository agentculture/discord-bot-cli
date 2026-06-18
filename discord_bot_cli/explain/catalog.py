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

## Introspection verbs

- `discord-bot-cli whoami` — identity probe from `culture.yaml`.
- `discord-bot-cli learn` — structured self-teaching prompt.
- `discord-bot-cli explain <path>` — markdown docs for any noun/verb.
- `discord-bot-cli overview` — descriptive snapshot of the agent.
- `discord-bot-cli doctor` — check the agent-identity invariants.
- `discord-bot-cli cli overview` — describe the CLI surface.

## Discord verbs

Need `$DISCORD_BOT_TOKEN` and the `[discord]` extra; one-shot (no daemon).

- `discord-bot-cli channel list|messages` — a guild's channels / a channel's messages.
- `discord-bot-cli message post|reply|react` — write to a channel.
- `discord-bot-cli thread create|post` — create a thread / post into one.
- `discord-bot-cli user get` — look up a user.

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

# --- Discord domain nouns -------------------------------------------------
#
# All Discord verbs need a bot token in $DISCORD_BOT_TOKEN and the optional
# `[discord]` extra (pip install 'discord-bot-cli[discord]'). They are one-shot:
# each connects over REST, performs one action, and exits. Missing token/extra
# → exit 2 with a hint; bad ids → exit 1.

_CHANNEL = """\
# discord-bot-cli channel

Read a guild's channels and a channel's messages.

## Verbs

- `discord-bot-cli channel list <guild_id>` — list a guild's channels.
- `discord-bot-cli channel messages <channel_id> [--limit N]` — read the last
  N messages (1-100, default 20), oldest first.
- `discord-bot-cli channel overview` — describe this noun.

## Usage

    DISCORD_BOT_TOKEN=... discord-bot-cli channel list 1234567890 --json
    DISCORD_BOT_TOKEN=... discord-bot-cli channel messages 1234567890 --limit 50 --json
"""

_MESSAGE = """\
# discord-bot-cli message

Post, reply to, and react to messages. `post`/`reply` return the created message
id so the output composes into the next verb.

## Verbs

- `discord-bot-cli message post <channel_id> <content>` — post a message.
- `discord-bot-cli message reply <channel_id> <message_id> <content>` — reply
  (attaches a message_reference to the target).
- `discord-bot-cli message react <channel_id> <message_id> <emoji>` — add a
  reaction (unicode emoji, or `name:id` for a custom one).
- `discord-bot-cli message overview` — describe this noun.

## Usage

    DISCORD_BOT_TOKEN=... discord-bot-cli message post 123 "hello" --json
    DISCORD_BOT_TOKEN=... discord-bot-cli message react 123 456 👍
"""

_THREAD = """\
# discord-bot-cli thread

Create threads and post to them.

## Verbs

- `discord-bot-cli thread create <channel_id> --name <name> [--message <id>]` —
  create a thread, anchored to a message or standalone (public). Returns the id.
- `discord-bot-cli thread post <thread_id> <content>` — post into a thread.
- `discord-bot-cli thread overview` — describe this noun.

## Usage

    DISCORD_BOT_TOKEN=... discord-bot-cli thread create 123 --name "triage" --json
    DISCORD_BOT_TOKEN=... discord-bot-cli thread post 789 "first post" --json
"""

_USER = """\
# discord-bot-cli user

Look up a Discord user.

## Verbs

- `discord-bot-cli user get <user_id>` — fetch a user's public profile
  (`id`, `username`, `global_name`, `bot`).
- `discord-bot-cli user overview` — describe this noun.

## Usage

    DISCORD_BOT_TOKEN=... discord-bot-cli user get 1234567890 --json
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
    # Discord domain nouns + their verbs.
    ("channel",): _CHANNEL,
    ("channel", "list"): _CHANNEL,
    ("channel", "messages"): _CHANNEL,
    ("channel", "overview"): _CHANNEL,
    ("message",): _MESSAGE,
    ("message", "post"): _MESSAGE,
    ("message", "reply"): _MESSAGE,
    ("message", "react"): _MESSAGE,
    ("message", "overview"): _MESSAGE,
    ("thread",): _THREAD,
    ("thread", "create"): _THREAD,
    ("thread", "post"): _THREAD,
    ("thread", "overview"): _THREAD,
    ("user",): _USER,
    ("user", "get"): _USER,
    ("user", "overview"): _USER,
}

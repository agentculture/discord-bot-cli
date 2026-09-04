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
  N messages (1-100, default 20), oldest first (so the newest is last).
- `discord-bot-cli channel messages <channel_id> --since <when> [--limit N]` —
  read every message newer than `<when>` (an ISO 8601 timestamp, a date-only
  `YYYY-MM-DD` meaning midnight UTC, or a duration like `90d`, units
  h/d/w/m where m is months). This pages past the 100-message cap; with
  `--since`, `--limit` becomes a safety ceiling on the walk, not a page size.
- `discord-bot-cli channel overview` — describe this noun.

## The `window` coverage signal

Every `--json` run of `channel messages` — plain or windowed — carries a
`window` object: `{"since", "limit", "message_count", "fully_covered",
"stopped_by"}`. `stopped_by` is one of `"limit"` (the ceiling cut the walk
short), `"window_end"` (a `--since` window was walked to completion —
`fully_covered` is only true here), or `"no_window"` (no `--since` was given,
so coverage is undefined and reported `false` rather than guessed). A count
that lands exactly on `--limit` is reported as `"limit"` — the pessimistic
reading, since the API can't say whether more messages existed.

## Usage

    DISCORD_BOT_TOKEN=... discord-bot-cli channel list 1234567890 --json
    DISCORD_BOT_TOKEN=... discord-bot-cli channel messages 1234567890 --limit 50 --json
    DISCORD_BOT_TOKEN=... discord-bot-cli channel messages 1234567890 --since 90d --json
"""

_MESSAGE = """\
# discord-bot-cli message

Post, reply to, and react to messages. `post`/`reply` return the created message
id so the output composes into the next verb.

## Verbs

- `discord-bot-cli message post <channel_id> [content] [--file PATH]...` —
  post a message, optionally with one or more local file attachments (up to
  10, repeatable). `content` may be omitted only if at least one `--file` is
  given — Discord allows a file-only message but never a fully empty one.
- `discord-bot-cli message reply <channel_id> <message_id> [content] [--file PATH]...` —
  reply (attaches a message_reference to the target), same content/`--file`
  rule as `post`.
- `discord-bot-cli message react <channel_id> <message_id> <emoji>` — add a
  reaction (unicode emoji, or `name:id` for a custom one).
- `discord-bot-cli message overview` — describe this noun.

## `--file` and attachments

`--file` reads a **local path the process can open — unsandboxed, with no
path allow-listing** — and uploads it to Discord (a third party); this CLI is
driven by other agents over the mesh, so which paths reach `--file` is the
operator's responsibility, not this CLI's. `--json` on `post`/`reply` adds an
`attachments` list, one entry per file: `{"id", "filename", "url", "size"}`.
That `url` is a **reference, not storage**. It is a signed CDN link carrying
`?ex=` (expiry), `&is=` (issued) and `&hm=` (signature) parameters, measured
at ~24h of validity — so it stops resolving on its own even while the message
still exists — and it 404s outright once the message is deleted. Re-fetch the
message for a fresh URL; never store one and expect it to keep working.

## Usage

    DISCORD_BOT_TOKEN=... discord-bot-cli message post 123 "hello" --json
    DISCORD_BOT_TOKEN=... discord-bot-cli message post 123 --file ./report.png --json
    DISCORD_BOT_TOKEN=... discord-bot-cli message react 123 456 👍
"""

_THREAD = """\
# discord-bot-cli thread

Create threads and post to them.

## Verbs

- `discord-bot-cli thread create <channel_id> --name <name> [--message <id>]` —
  create a thread, anchored to a message or standalone (public). Returns the id.
- `discord-bot-cli thread post <thread_id> [content] [--file PATH]...` — post
  into a thread, optionally with one or more local file attachments (up to
  10, repeatable); `content` may be omitted only if at least one `--file` is
  given, same rule and payload as `message post`/`reply`.
- `discord-bot-cli thread overview` — describe this noun.

## `--file` and attachments

Same seam as `message post`/`reply`: `--file` is an **unsandboxed local
read** — any path the process can open is uploaded to Discord, with no path
allow-listing, so the operator owns which paths reach the flag. `--json`
adds an `attachments` list (`{"id", "filename", "url", "size"}` per file);
that `url` is a **reference, not storage** — it 404s once the message is
deleted.

## Usage

    DISCORD_BOT_TOKEN=... discord-bot-cli thread create 123 --name "triage" --json
    DISCORD_BOT_TOKEN=... discord-bot-cli thread post 789 "first post" --json
    DISCORD_BOT_TOKEN=... discord-bot-cli thread post 789 --file ./log.txt --json
"""

_USER = """\
# discord-bot-cli user

Look up one or more Discord users.

## Verbs

- `discord-bot-cli user get <user_id> [<user_id> ...] [--ids-file <path>|-]` —
  fetch public profile fields (`id`, `username`, `global_name`, `bot`) for a
  batch of users, resolved sequentially in input order (positional ids first,
  then `--ids-file` lines). A per-id lookup failure is recorded as an
  `{"id", "error", "remediation"}` entry in the same position rather than
  failing the whole batch — the process still exits 0.
- `discord-bot-cli user overview` — describe this noun.

## `--json` is always an array

`user get --json` **always** emits a JSON array, even for a single id — this
changed in **0.6.0**, a deliberate breaking change from the prior payload,
which returned a single object for a single id. Callers written against the
old single-object shape must update to index/iterate the array.

## Usage

    DISCORD_BOT_TOKEN=... discord-bot-cli user get 1234567890 --json
    DISCORD_BOT_TOKEN=... discord-bot-cli user get 111 222 333 --json
    DISCORD_BOT_TOKEN=... discord-bot-cli user get --ids-file ids.txt --json
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

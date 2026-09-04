# discord-bot-cli

Agent + CLI that gives an agent Discord access via a bot.

## What you get

- **An agent-first CLI** cited from [teken](https://github.com/agentculture/teken)
  (`afi-cli`) — the runtime package has no third-party dependencies.
- **A mesh identity** — `culture.yaml` (`suffix` + `backend`) and the matching
  prompt file (`CLAUDE.md` for `backend: claude`).
- **The canonical guildmaster skill kit** (11 skills) under `.claude/skills/`,
  vendored cite-don't-import. See [`docs/skill-sources.md`](docs/skill-sources.md).
- **A build + deploy baseline** — pytest, lint, the agent-first rubric gate, and
  PyPI Trusted Publishing wired into GitHub Actions.

## Quickstart

```bash
uv sync
uv run pytest -n auto                 # run the test suite
uv run discord-bot-cli whoami  # identity from culture.yaml
uv run discord-bot-cli learn   # self-teaching prompt (add --json)
uv run teken cli doctor . --strict    # the agent-first rubric gate CI runs
```

## CLI

### Introspection verbs

| Verb | What it does |
|------|--------------|
| `whoami` | Report this agent's nick, version, backend, and model from `culture.yaml`. |
| `learn` | Print a structured self-teaching prompt. |
| `explain <path>` | Markdown docs for any noun/verb path. |
| `overview` | Read-only descriptive snapshot of the agent. |
| `doctor` | Check the agent-identity invariants (prompt-file-present, backend-consistency). |
| `cli overview` | Describe the CLI surface itself. |

Every command supports `--json`. Results go to stdout, errors/diagnostics to
stderr (never mixed). Exit codes: `0` success, `1` user error, `2` environment
error, `3+` reserved.

### Discord verbs

Give an agent Discord access through a bot. These need a bot token and the
optional `discord` extra (which pulls in `discord.py`):

```bash
uv pip install 'discord-bot-cli[discord]'   # or: pip install 'discord-bot-cli[discord]'
export DISCORD_BOT_TOKEN=...                 # read from the env, never a flag
```

| Verb | What it does |
|------|--------------|
| `channel list <guild_id>` | List a guild's channels. |
| `channel messages <channel_id> [--limit N]` | Read the last N messages (1–100, default 20). |
| `channel messages <channel_id> --since W [--limit N]` | Read a time window, paging past the 100-message cap. `W` is an ISO 8601 timestamp, a date (`2026-06-01`, midnight UTC), or a duration (`90d`). `--limit` becomes a safety ceiling. |
| `message post <channel_id> [content] [--file PATH]...` | Post a message, optionally with attachments; returns its id. |
| `message reply <channel_id> <message_id> [content] [--file PATH]...` | Reply to a message, optionally with attachments. |
| `message react <channel_id> <message_id> <emoji>` | Add a reaction. |
| `thread create <channel_id> --name <name> [--message <id>]` | Create a thread (anchored or standalone). |
| `thread post <thread_id> [content] [--file PATH]...` | Post into a thread, optionally with attachments. |
| `user get <user_id> [<user_id> ...] [--ids-file <path>\|-]` | Look up one or more users. `--json` is **always** an array. |

Each verb is **one-shot**: it connects, performs one action, and exits (no
daemon, no gateway subscription). `post`/`reply`/`thread create` return the
created id in `--json` so output composes into the next call. A missing token or
the absent extra exits `2` with a hint; bad ids exit `1`.

```bash
# discover, read, write, compose
discord channel list 1234567890 --json
discord channel messages 1234567890 --limit 50 --json
MSG=$(discord message post 1234567890 "hello" --json | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
discord message react 1234567890 "$MSG" 👍

# attach files (repeatable; content optional when a file is given)
discord message post 1234567890 "weekly report" --file chart.svg --file table.png --json

# read a real time window, then batch-resolve the authors in one login
discord channel messages 1234567890 --since 90d --json > scan.json
python3 -c 'import json;print("\n".join({m["author"]["id"] for m in json.load(open("scan.json"))["messages"] if not m["author"]["bot"]}))' \
  | discord user get --ids-file - --json
```

`--since` reads carry a `window` object in `--json` —
`{since, limit, message_count, fully_covered, stopped_by}` — so a caller can
tell a truncated scan from a complete one rather than guessing. Two things to
know before reaching for `--file`: it is an **unsandboxed local read** (any path
the process can open is uploaded to Discord — the operator owns which paths
reach it), and the returned attachment `url` is a **reference, not storage**: it
a signed CDN link that expires roughly 24h after it is issued, and 404s
outright once the message is deleted — re-fetch the message for a fresh one.

> The runtime package itself stays dependency-free — `discord.py` is imported
> lazily inside the verb handlers, so a plain install never pulls it in.

### Live Discord tests

`uv run pytest` never talks to real Discord — the whole suite runs against a
stubbed client. `tests/test_live_discord.py` is a separate, opt-in lane (marker
`live`) that drives the real bot; it self-skips unless **both**
`DISCORD_LIVE_TESTS=1` and `DISCORD_BOT_TOKEN` are set. **These tests leave
permanent artifacts** — messages, replies, reactions, threads, and a real
`message post --file` upload — because there is no `delete` verb, so always
point `DISCORD_TEST_CHANNEL_ID` at a disposable sandbox channel, never a real
one. See [`CLAUDE.md`](CLAUDE.md) for the full env-var list and how to run
them.

## Make it your own

1. Rename the package `discord_bot_cli/` and the `discord-bot-cli`
   CLI/dist name throughout `pyproject.toml`, the package, `tests/`,
   `sonar-project.properties`, and this `README.md`. The name is hard-coded in
   ~100 places, so list every occurrence first — see the `git grep` discovery
   command in [`CLAUDE.md`](CLAUDE.md), the authoritative rename procedure.
2. Edit `culture.yaml` with your `suffix` and `backend`.
3. Rewrite `CLAUDE.md` for your agent and run `/init`.
4. Re-vendor only the skills you need from guildmaster (see
   [`docs/skill-sources.md`](docs/skill-sources.md)).

See [`CLAUDE.md`](CLAUDE.md) for the full conventions (version-bump-every-PR,
the `cicd` PR lane, deploy setup).

## License

MIT — see [`LICENSE`](LICENSE).

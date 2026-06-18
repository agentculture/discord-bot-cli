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
| `message post <channel_id> <content>` | Post a message; returns its id. |
| `message reply <channel_id> <message_id> <content>` | Reply to a message. |
| `message react <channel_id> <message_id> <emoji>` | Add a reaction. |
| `thread create <channel_id> --name <name> [--message <id>]` | Create a thread (anchored or standalone). |
| `thread post <thread_id> <content>` | Post a message into a thread. |
| `user get <user_id>` | Look up a user's public profile. |

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
```

> The runtime package itself stays dependency-free — `discord.py` is imported
> lazily inside the verb handlers, so a plain install never pulls it in.

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

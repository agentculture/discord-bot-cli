"""``discord-bot-cli learn`` — the learnability affordance.

Prints a structured self-teaching prompt. Must satisfy the agent-first rubric:
>=200 chars and mention purpose, command map, exit codes, --json, and explain.
"""

from __future__ import annotations

import argparse

from discord_bot_cli import __version__
from discord_bot_cli.cli._output import emit_result

_TEXT = """\
discord-bot-cli — a clonable template for AgentCulture mesh agents.

Purpose
-------
Scaffold for a new Culture mesh agent: an agent-first CLI (cited from the teken
`python-cli` reference), an identity (culture.yaml + CLAUDE.md), the canonical
guildmaster skill kit under .claude/skills/, and a deploy/CI baseline. Clone it,
rename the package, and edit culture.yaml to mint a new agent.

Introspection commands
----------------------
  discord-bot-cli whoami             Identity from culture.yaml.
  discord-bot-cli learn              This self-teaching prompt.
  discord-bot-cli explain <path>...  Markdown docs for any noun/verb path.
  discord-bot-cli overview           Descriptive snapshot of the agent.
  discord-bot-cli doctor             Check the agent-identity invariants.
  discord-bot-cli cli overview       Describe the CLI surface itself.

Discord commands (need $DISCORD_BOT_TOKEN + the [discord] extra; one-shot)
-------------------------------------------------------------------------
  discord-bot-cli channel list <guild_id>
  discord-bot-cli channel messages <channel_id> [--since W] [--limit N]
  discord-bot-cli message post <channel_id> [content] [--file PATH]...
  discord-bot-cli message reply <channel_id> <message_id> [content] [--file PATH]...
  discord-bot-cli message react <channel_id> <message_id> <emoji>
  discord-bot-cli thread create <channel_id> --name <name> [--message <id>]
  discord-bot-cli thread post <thread_id> [content] [--file PATH]...
  discord-bot-cli user get <user_id> [<user_id> ...] [--ids-file <path>|-]

Notes on the flags above
-------------------------
  --since accepts an ISO 8601 timestamp, a date 'YYYY-MM-DD' (midnight UTC),
    or a duration like '90d' (h/d/w/m); channel messages --json always
    carries a "window" coverage object ({since, limit, message_count,
    fully_covered, stopped_by}), even on plain reads.
  --file is repeatable (up to 10) and is an UNSANDBOXED LOCAL READ: any path
    this process can open is uploaded to Discord, with no path allow-listing.
    content may be omitted only if at least one --file is given. --json adds
    an "attachments" list ({id, filename, url, size}); the url is a
    REFERENCE, NOT STORAGE — it 404s once the message is deleted.
  user get --json ALWAYS emits an array, even for one id (breaking change in
    0.6.0 from the prior single-object payload). A bad id becomes an
    {id, error, remediation} entry in place rather than failing the batch.

Machine-readable output
-----------------------
Every command supports --json. Errors in JSON mode emit
{"code", "message", "remediation"} to stderr. Stdout and stderr never mix.

Exit-code policy
----------------
  0 success
  1 user-input error (bad flag, bad path, missing arg)
  2 environment / setup error
  3+ reserved

More detail
-----------
  discord-bot-cli explain discord-bot-cli
"""


def _as_json_payload() -> dict[str, object]:
    return {
        "tool": "discord-bot-cli",
        "version": __version__,
        "purpose": "Clonable scaffold for a new AgentCulture mesh agent.",
        "commands": [
            {"path": ["whoami"], "summary": "Identity probe from culture.yaml."},
            {"path": ["learn"], "summary": "Self-teaching prompt."},
            {"path": ["explain"], "summary": "Markdown docs by path."},
            {"path": ["overview"], "summary": "Descriptive snapshot of the agent."},
            {"path": ["doctor"], "summary": "Check the agent-identity invariants."},
            {"path": ["cli", "overview"], "summary": "Describe the CLI surface."},
            {"path": ["channel", "list"], "summary": "List a guild's channels."},
            {
                "path": ["channel", "messages"],
                "summary": (
                    "Read messages: --limit N (last N, default 20) or --since W "
                    "(pages past the 100-message cap); --json always carries a "
                    "window coverage signal."
                ),
            },
            {
                "path": ["message", "post"],
                "summary": (
                    "Post a message to a channel; content optional if --file is "
                    "given (repeatable, up to 10, unsandboxed local read)."
                ),
            },
            {
                "path": ["message", "reply"],
                "summary": (
                    "Reply to a message; same optional content / --file rule as " "message post."
                ),
            },
            {"path": ["message", "react"], "summary": "Add a reaction to a message."},
            {"path": ["thread", "create"], "summary": "Create a thread (anchored or standalone)."},
            {
                "path": ["thread", "post"],
                "summary": (
                    "Post into a thread; content optional if --file is given, "
                    "same attachment rules as message post."
                ),
            },
            {
                "path": ["user", "get"],
                "summary": (
                    "Look up one or more Discord users, in input order; --json is "
                    "always an array, even for a single id."
                ),
            },
        ],
        "discord_auth": {
            "token_env": "DISCORD_BOT_TOKEN",
            "extra": "pip install 'discord-bot-cli[discord]'",
        },
        "exit_codes": {
            "0": "success",
            "1": "user-input error",
            "2": "environment/setup error",
        },
        "json_support": True,
        "explain_pointer": "discord-bot-cli explain <path>",
        "boundaries": {
            "--file": (
                "unsandboxed local read: any path the process can open is "
                "uploaded to Discord, with no path allow-listing"
            ),
            "attachment_url": "a reference, not storage — 404s once the message is deleted",
            "user_get_json_shape": (
                "always an array, even for a single id (breaking change in 0.6.0 "
                "from the prior single-object payload)"
            ),
        },
    }


def cmd_learn(args: argparse.Namespace) -> int:
    if getattr(args, "json", False):
        emit_result(_as_json_payload(), json_mode=True)
    else:
        emit_result(_TEXT, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "learn",
        help="Print a structured self-teaching prompt for agent consumers.",
    )
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_learn)

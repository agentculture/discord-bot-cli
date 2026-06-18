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
  discord-bot-cli channel messages <channel_id> [--limit N]
  discord-bot-cli message post <channel_id> <content>
  discord-bot-cli message reply <channel_id> <message_id> <content>
  discord-bot-cli message react <channel_id> <message_id> <emoji>
  discord-bot-cli thread create <channel_id> --name <name> [--message <id>]
  discord-bot-cli thread post <thread_id> <content>
  discord-bot-cli user get <user_id>

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
            {"path": ["channel", "messages"], "summary": "Read the last N messages of a channel."},
            {"path": ["message", "post"], "summary": "Post a message to a channel."},
            {"path": ["message", "reply"], "summary": "Reply to a message."},
            {"path": ["message", "react"], "summary": "Add a reaction to a message."},
            {"path": ["thread", "create"], "summary": "Create a thread (anchored or standalone)."},
            {"path": ["thread", "post"], "summary": "Post a message into a thread."},
            {"path": ["user", "get"], "summary": "Look up a Discord user."},
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

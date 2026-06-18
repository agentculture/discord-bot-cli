"""Shared helpers for the Discord noun verbs (channel/message/thread/user).

Keeps the per-noun modules tight: a uniform ``overview`` renderer (every noun
with action-verbs must expose ``overview`` per the agent-first rubric) and the
shared auth/conventions note. The actual Discord I/O lives in
:mod:`discord_bot_cli.discord_client`; these helpers are pure formatting.
"""

from __future__ import annotations

import argparse

from discord_bot_cli.cli._commands.overview import emit_overview
from discord_bot_cli.discord_client import TOKEN_ENV

_AUTH = [
    f"requires a bot token in ${TOKEN_ENV} (read from the env, never a flag)",
    "needs the optional extra: pip install 'discord-bot-cli[discord]'",
]

_CONVENTIONS = [
    "ids are plain positional args; results are machine-parseable with --json",
    "one-shot: each verb connects, acts, and exits (no daemon)",
    "exit codes: 0 ok, 1 user error, 2 environment error (missing token/extra)",
]


def emit_noun_overview(noun: str, verbs: list[str], *, json_mode: bool) -> None:
    """Render the standard overview for a Discord noun."""
    sections = [
        {"title": "Verbs", "items": list(verbs)},
        {"title": "Auth", "items": list(_AUTH)},
        {"title": "Conventions", "items": list(_CONVENTIONS)},
    ]
    emit_overview(f"discord-bot-cli {noun}", sections, json_mode=json_mode)


def add_json(parser: argparse.ArgumentParser) -> None:
    """Attach the conventional ``--json`` flag."""
    parser.add_argument("--json", action="store_true", help="Emit structured JSON.")

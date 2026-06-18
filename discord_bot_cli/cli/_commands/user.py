"""``discord-bot-cli user`` — look up a Discord user.

Verbs:

* ``user get <user_id>`` — fetch a user's public profile fields.
* ``user overview`` — describe this noun.

All Discord I/O routes through :func:`discord_bot_cli.discord_client.run`.
"""

from __future__ import annotations

import argparse

from discord_bot_cli import discord_client
from discord_bot_cli.cli._commands._discord_common import add_json, emit_noun_overview
from discord_bot_cli.cli._output import emit_result

_VERBS = [
    "user get <user_id> — fetch a user's public profile",
    "user overview — describe this noun (this command)",
]


def cmd_user_get(args: argparse.Namespace) -> int:
    user_id = discord_client.parse_id(args.user_id, "user_id")

    async def action(client: object) -> dict[str, object]:
        user = await client.fetch_user(user_id)
        return {
            "id": str(user.id),
            "username": user.name,
            "global_name": getattr(user, "global_name", None),
            "bot": bool(getattr(user, "bot", False)),
        }

    result = discord_client.run(action)
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result(result, json_mode=True)
    else:
        emit_result(
            f"{result['id']}  {result['username']} "
            f"(global_name={result['global_name']}, bot={result['bot']})",
            json_mode=False,
        )
    return 0


def cmd_user_overview(args: argparse.Namespace) -> int:
    emit_noun_overview("user", _VERBS, json_mode=bool(getattr(args, "json", False)))
    return 0


def _no_verb(args: argparse.Namespace) -> int:
    return cmd_user_overview(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("user", help="Look up a Discord user.")
    add_json(p)
    p.set_defaults(func=_no_verb, json=False)
    noun_sub = p.add_subparsers(dest="user_command", parser_class=type(p))

    pg = noun_sub.add_parser("get", help="Fetch a user's public profile.")
    pg.add_argument("user_id", help="Numeric user id.")
    add_json(pg)
    pg.set_defaults(func=cmd_user_get)

    ov = noun_sub.add_parser("overview", help="Describe the user noun.")
    add_json(ov)
    ov.set_defaults(func=cmd_user_overview)

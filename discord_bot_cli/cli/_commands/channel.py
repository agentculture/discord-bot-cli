"""``discord-bot-cli channel`` — read a guild's channels and a channel's messages.

Verbs:

* ``channel list <guild_id>`` — the channels of a guild the bot is in.
* ``channel messages <channel_id> [--limit N]`` — the last N messages, oldest
  first (so the newest is last, the natural reading order).
* ``channel overview`` — describe this noun.

All Discord I/O routes through :func:`discord_bot_cli.discord_client.run`.
"""

from __future__ import annotations

import argparse

from discord_bot_cli import discord_client
from discord_bot_cli.cli._commands._discord_common import add_json, emit_noun_overview
from discord_bot_cli.cli._errors import EXIT_USER_ERROR, CliError
from discord_bot_cli.cli._output import emit_result

_VERBS = [
    "channel list <guild_id> — list the channels of a guild",
    "channel messages <channel_id> [--limit N] — read the last N messages",
    "channel overview — describe this noun (this command)",
]

_LIMIT_MIN = 1
_LIMIT_MAX = 100
_LIMIT_DEFAULT = 20


def _message_dict(message: object) -> dict[str, object]:
    author = getattr(message, "author", None)
    created = getattr(message, "created_at", None)
    return {
        "id": str(getattr(message, "id", "")),
        "author": {
            "id": str(getattr(author, "id", "")),
            "name": getattr(author, "name", None),
        },
        "content": getattr(message, "content", ""),
        "created_at": created.isoformat() if created is not None else None,
    }


def cmd_channel_list(args: argparse.Namespace) -> int:
    guild_id = discord_client.parse_id(args.guild_id, "guild_id")

    async def action(client: object) -> list[dict[str, object]]:
        guild = await client.fetch_guild(guild_id)
        channels = await guild.fetch_channels()
        return [
            {"id": str(c.id), "name": c.name, "type": str(getattr(c.type, "name", c.type))}
            for c in channels
        ]

    channels = discord_client.run(action)
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result({"guild_id": str(guild_id), "channels": channels}, json_mode=True)
    else:
        lines = [f"{c['id']}  {c['type']:<16} {c['name']}" for c in channels]
        emit_result("\n".join(lines) if lines else "(no channels)", json_mode=False)
    return 0


def cmd_channel_messages(args: argparse.Namespace) -> int:
    channel_id = discord_client.parse_id(args.channel_id, "channel_id")
    if not _LIMIT_MIN <= args.limit <= _LIMIT_MAX:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"--limit must be between {_LIMIT_MIN} and {_LIMIT_MAX}, got {args.limit}",
            remediation=f"pass --limit in [{_LIMIT_MIN}, {_LIMIT_MAX}]",
        )

    async def action(client: object) -> list[dict[str, object]]:
        channel = await client.fetch_channel(channel_id)
        collected = [m async for m in channel.history(limit=args.limit)]
        collected.reverse()  # history yields newest-first; emit oldest-first
        return [_message_dict(m) for m in collected]

    messages = discord_client.run(action)
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result({"channel_id": str(channel_id), "messages": messages}, json_mode=True)
    else:
        lines = [f"{m['id']}  {m['author']['name']}: {m['content']}" for m in messages]
        emit_result("\n".join(lines) if lines else "(no messages)", json_mode=False)
    return 0


def cmd_channel_overview(args: argparse.Namespace) -> int:
    emit_noun_overview("channel", _VERBS, json_mode=bool(getattr(args, "json", False)))
    return 0


def _no_verb(args: argparse.Namespace) -> int:
    return cmd_channel_overview(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("channel", help="Read a guild's channels and a channel's messages.")
    add_json(p)
    p.set_defaults(func=_no_verb, json=False)
    noun_sub = p.add_subparsers(dest="channel_command", parser_class=type(p))

    pl = noun_sub.add_parser("list", help="List the channels of a guild.")
    pl.add_argument("guild_id", help="Numeric guild (server) id.")
    add_json(pl)
    pl.set_defaults(func=cmd_channel_list)

    pm = noun_sub.add_parser("messages", help="Read the last N messages of a channel.")
    pm.add_argument("channel_id", help="Numeric channel id.")
    pm.add_argument(
        "--limit",
        type=int,
        default=_LIMIT_DEFAULT,
        help=f"How many messages to read ({_LIMIT_MIN}-{_LIMIT_MAX}, default {_LIMIT_DEFAULT}).",
    )
    add_json(pm)
    pm.set_defaults(func=cmd_channel_messages)

    ov = noun_sub.add_parser("overview", help="Describe the channel noun.")
    add_json(ov)
    ov.set_defaults(func=cmd_channel_overview)

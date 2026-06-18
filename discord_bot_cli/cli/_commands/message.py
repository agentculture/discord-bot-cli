"""``discord-bot-cli message`` — post, reply to, and react to messages.

Verbs:

* ``message post <channel_id> <content>`` — post a message; returns its id.
* ``message reply <channel_id> <message_id> <content>`` — reply with a
  message_reference to the target.
* ``message react <channel_id> <message_id> <emoji>`` — add a reaction.
* ``message overview`` — describe this noun.

``post``/``reply`` emit the created message id so an agent can feed it into the
next verb. All Discord I/O routes through
:func:`discord_bot_cli.discord_client.run`.
"""

from __future__ import annotations

import argparse

from discord_bot_cli import discord_client
from discord_bot_cli.cli._commands._discord_common import add_json, emit_noun_overview
from discord_bot_cli.cli._output import emit_result

_VERBS = [
    "message post <channel_id> <content> — post a message",
    "message reply <channel_id> <message_id> <content> — reply to a message",
    "message react <channel_id> <message_id> <emoji> — add a reaction",
    "message overview — describe this noun (this command)",
]


def cmd_message_post(args: argparse.Namespace) -> int:
    channel_id = discord_client.parse_id(args.channel_id, "channel_id")

    async def action(client: object) -> dict[str, object]:
        channel = await client.fetch_channel(channel_id)
        message = await channel.send(args.content)
        return {"id": str(message.id), "channel_id": str(channel_id)}

    result = discord_client.run(action)
    _emit(result, f"posted message {result['id']}", json_mode=bool(getattr(args, "json", False)))
    return 0


def cmd_message_reply(args: argparse.Namespace) -> int:
    channel_id = discord_client.parse_id(args.channel_id, "channel_id")
    message_id = discord_client.parse_id(args.message_id, "message_id")

    async def action(client: object) -> dict[str, object]:
        channel = await client.fetch_channel(channel_id)
        target = await channel.fetch_message(message_id)
        reply = await target.reply(args.content)
        return {
            "id": str(reply.id),
            "channel_id": str(channel_id),
            "in_reply_to": str(message_id),
        }

    result = discord_client.run(action)
    _emit(
        result, f"replied with message {result['id']}", json_mode=bool(getattr(args, "json", False))
    )
    return 0


def cmd_message_react(args: argparse.Namespace) -> int:
    channel_id = discord_client.parse_id(args.channel_id, "channel_id")
    message_id = discord_client.parse_id(args.message_id, "message_id")

    async def action(client: object) -> dict[str, object]:
        channel = await client.fetch_channel(channel_id)
        target = await channel.fetch_message(message_id)
        await target.add_reaction(args.emoji)
        return {"message_id": str(message_id), "emoji": args.emoji, "reacted": True}

    result = discord_client.run(action)
    _emit(
        result,
        f"reacted {args.emoji} to message {message_id}",
        json_mode=bool(getattr(args, "json", False)),
    )
    return 0


def cmd_message_overview(args: argparse.Namespace) -> int:
    emit_noun_overview("message", _VERBS, json_mode=bool(getattr(args, "json", False)))
    return 0


def _emit(result: dict[str, object], human: str, *, json_mode: bool) -> None:
    emit_result(result if json_mode else human, json_mode=json_mode)


def _no_verb(args: argparse.Namespace) -> int:
    return cmd_message_overview(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("message", help="Post, reply to, and react to messages.")
    add_json(p)
    p.set_defaults(func=_no_verb, json=False)
    noun_sub = p.add_subparsers(dest="message_command", parser_class=type(p))

    pp = noun_sub.add_parser("post", help="Post a message to a channel.")
    pp.add_argument("channel_id", help="Numeric channel id.")
    pp.add_argument("content", help="Message text.")
    add_json(pp)
    pp.set_defaults(func=cmd_message_post)

    pr = noun_sub.add_parser("reply", help="Reply to a message.")
    pr.add_argument("channel_id", help="Numeric channel id.")
    pr.add_argument("message_id", help="Numeric id of the message to reply to.")
    pr.add_argument("content", help="Reply text.")
    add_json(pr)
    pr.set_defaults(func=cmd_message_reply)

    prx = noun_sub.add_parser("react", help="Add a reaction to a message.")
    prx.add_argument("channel_id", help="Numeric channel id.")
    prx.add_argument("message_id", help="Numeric id of the message to react to.")
    prx.add_argument("emoji", help="Emoji (unicode like 👍 or 'name:id' for a custom emoji).")
    add_json(prx)
    prx.set_defaults(func=cmd_message_react)

    ov = noun_sub.add_parser("overview", help="Describe the message noun.")
    add_json(ov)
    ov.set_defaults(func=cmd_message_overview)

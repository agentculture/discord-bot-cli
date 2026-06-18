"""``discord-bot-cli thread`` — create threads and post to them.

Verbs:

* ``thread create <channel_id> --name <name> [--message <message_id>]`` — create
  a thread, either anchored to an existing message or standalone (a public
  thread on the channel). Returns the new thread id.
* ``thread post <thread_id> <content>`` — post a message into a thread.
* ``thread overview`` — describe this noun.

All Discord I/O routes through :func:`discord_bot_cli.discord_client.run`.
"""

from __future__ import annotations

import argparse

from discord_bot_cli import discord_client
from discord_bot_cli.cli._commands._discord_common import add_json, emit_noun_overview
from discord_bot_cli.cli._output import emit_result

_VERBS = [
    "thread create <channel_id> --name <name> [--message <id>] — create a thread",
    "thread post <thread_id> <content> — post into a thread",
    "thread overview — describe this noun (this command)",
]


def cmd_thread_create(args: argparse.Namespace) -> int:
    channel_id = discord_client.parse_id(args.channel_id, "channel_id")
    message_id = discord_client.parse_id(args.message, "message_id") if args.message else None

    async def action(client: object) -> dict[str, object]:
        channel = await client.fetch_channel(channel_id)
        if message_id is not None:
            anchor = await channel.fetch_message(message_id)
            thread = await anchor.create_thread(name=args.name)
        else:
            discord = discord_client.require_discord()
            thread = await channel.create_thread(
                name=args.name, type=discord.ChannelType.public_thread
            )
        return {
            "id": str(thread.id),
            "name": thread.name,
            "channel_id": str(channel_id),
            "anchored_to": str(message_id) if message_id is not None else None,
        }

    result = discord_client.run(action)
    _emit(result, f"created thread {result['id']}", json_mode=bool(getattr(args, "json", False)))
    return 0


def cmd_thread_post(args: argparse.Namespace) -> int:
    thread_id = discord_client.parse_id(args.thread_id, "thread_id")

    async def action(client: object) -> dict[str, object]:
        thread = await client.fetch_channel(thread_id)
        message = await thread.send(args.content)
        return {"id": str(message.id), "thread_id": str(thread_id)}

    result = discord_client.run(action)
    _emit(
        result,
        f"posted message {result['id']} to thread {thread_id}",
        json_mode=bool(getattr(args, "json", False)),
    )
    return 0


def cmd_thread_overview(args: argparse.Namespace) -> int:
    emit_noun_overview("thread", _VERBS, json_mode=bool(getattr(args, "json", False)))
    return 0


def _emit(result: dict[str, object], human: str, *, json_mode: bool) -> None:
    emit_result(result if json_mode else human, json_mode=json_mode)


def _no_verb(args: argparse.Namespace) -> int:
    return cmd_thread_overview(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("thread", help="Create threads and post to them.")
    add_json(p)
    p.set_defaults(func=_no_verb, json=False)
    noun_sub = p.add_subparsers(dest="thread_command", parser_class=type(p))

    pc = noun_sub.add_parser("create", help="Create a thread (anchored or standalone).")
    pc.add_argument("channel_id", help="Numeric channel id the thread lives in.")
    pc.add_argument("--name", required=True, help="Thread name.")
    pc.add_argument(
        "--message",
        help="Optional message id to anchor the thread to (omit for a standalone public thread).",
    )
    add_json(pc)
    pc.set_defaults(func=cmd_thread_create)

    pp = noun_sub.add_parser("post", help="Post a message into a thread.")
    pp.add_argument("thread_id", help="Numeric thread id.")
    pp.add_argument("content", help="Message text.")
    add_json(pp)
    pp.set_defaults(func=cmd_thread_post)

    ov = noun_sub.add_parser("overview", help="Describe the thread noun.")
    add_json(ov)
    ov.set_defaults(func=cmd_thread_overview)

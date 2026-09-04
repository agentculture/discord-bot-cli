"""``discord-bot-cli channel`` — read a guild's channels and a channel's messages.

Verbs:

* ``channel list <guild_id>`` — the channels of a guild the bot is in.
* ``channel messages <channel_id> [--since W] [--limit N]`` — messages, always
  oldest first (so the newest is last, the natural reading order).
* ``channel overview`` — describe this noun.

All Discord I/O routes through :func:`discord_bot_cli.discord_client.run`.

Two read modes
--------------

*Plain* (``--limit N``, default 20, range 1-100): the last N messages — a
single page, the historical behaviour.

*Windowed* (``--since W``, parsed by
:func:`discord_bot_cli.cli._commands._timewindow.parse_since`): every message
newer than the window start. There is no 100-message ceiling here — the walk
is handed to discord.py with ``limit=None``, which pages internally (100 per
round-trip) until the channel runs out. ``--limit N`` may be combined with
``--since`` as a *safety ceiling* on that walk; there it is not capped at 100.

Ordering, and the trap under it
-------------------------------

``Messageable.history``'s ``oldest_first`` defaults to ``True`` when ``after``
is given and ``False`` otherwise (discord.py 2.7.1, ``discord/abc.py``:
``reverse = after is not None``). So the direction silently flips the moment a
window is requested, and a blanket ``collected.reverse()`` would emit a
windowed read *newest*-first — the opposite of this module's contract. We
therefore pass ``oldest_first=`` **explicitly** on every call and reverse only
when we asked for newest-first. Both paths are ordering-asserted in the tests.

The window coverage signal
--------------------------

Every ``--json`` run of ``channel messages`` carries a ``window`` object — on
plain reads too, so a caller can assert on it unconditionally:

.. code-block:: json

    {"since": "2026-06-01T00:00:00+00:00" | null,
     "limit": 50 | null,
     "message_count": 50,
     "fully_covered": false,
     "stopped_by": "limit" | "window_end" | "no_window"}

``fully_covered`` is true only when a ``--since`` window was walked to its end
(``stopped_by`` = ``window_end``). ``limit`` means the ceiling cut the walk
short; ``no_window`` means no window was requested, so coverage is undefined
and reported as ``false`` rather than guessed. When the collected count lands
exactly on ``--limit`` we report ``limit``: the walk stopped at the ceiling and
the API cannot tell us whether the next message existed. That is deliberately
the pessimistic reading — better a spurious "come back for more" than a false
"you have everything".
"""

from __future__ import annotations

import argparse
from datetime import datetime

from discord_bot_cli import discord_client
from discord_bot_cli.cli._commands._discord_common import add_json, emit_noun_overview
from discord_bot_cli.cli._commands._timewindow import parse_since
from discord_bot_cli.cli._errors import EXIT_USER_ERROR, CliError
from discord_bot_cli.cli._output import emit_diagnostic, emit_result

_VERBS = [
    "channel list <guild_id> — list the channels of a guild",
    "channel messages <channel_id> [--limit N] — read the last N messages",
    "channel messages <channel_id> --since 90d [--limit N] — read a time window,"
    " paging past the 100-message cap (--limit becomes a safety ceiling)",
    "channel overview — describe this noun (this command)",
]

_LIMIT_MIN = 1
_LIMIT_MAX = 100
_LIMIT_DEFAULT = 20

_STOPPED_BY_LIMIT = "limit"
_STOPPED_BY_WINDOW_END = "window_end"
_STOPPED_BY_NO_WINDOW = "no_window"


def _message_dict(message: object) -> dict[str, object]:
    author = getattr(message, "author", None)
    created = getattr(message, "created_at", None)
    return {
        "id": str(getattr(message, "id", "")),
        "author": {
            "id": str(getattr(author, "id", "")),
            "name": getattr(author, "name", None),
            "bot": bool(getattr(author, "bot", False)),
            "global_name": getattr(author, "global_name", None),
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


def _resolve_limit(limit: int | None, windowed: bool) -> int | None:
    """Validate ``--limit`` and return the value to hand to ``history``.

    Plain reads keep the historical 1-100 page-size check and default. A
    windowed read has no upper bound (the walk pages), so only the lower bound
    applies; ``None`` there means "walk the whole window".
    """
    if not windowed:
        effective = _LIMIT_DEFAULT if limit is None else limit
        if not _LIMIT_MIN <= effective <= _LIMIT_MAX:
            raise CliError(
                code=EXIT_USER_ERROR,
                message=f"--limit must be between {_LIMIT_MIN} and {_LIMIT_MAX}, got {effective}",
                remediation=f"pass --limit in [{_LIMIT_MIN}, {_LIMIT_MAX}], or use --since",
            )
        return effective
    if limit is not None and limit < _LIMIT_MIN:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"--limit must be at least {_LIMIT_MIN}, got {limit}",
            remediation="with --since, --limit is a safety ceiling on the walk; pass 1 or more",
        )
    return limit


def _window_signal(since: datetime | None, limit: int | None, count: int) -> dict[str, object]:
    """Build the always-present coverage signal (see the module docstring)."""
    if since is None:
        stopped_by = _STOPPED_BY_NO_WINDOW
    elif limit is not None and count >= limit:
        stopped_by = _STOPPED_BY_LIMIT
    else:
        stopped_by = _STOPPED_BY_WINDOW_END
    return {
        "since": since.isoformat() if since is not None else None,
        "limit": limit,
        "message_count": count,
        "fully_covered": stopped_by == _STOPPED_BY_WINDOW_END,
        "stopped_by": stopped_by,
    }


def cmd_channel_messages(args: argparse.Namespace) -> int:
    channel_id = discord_client.parse_id(args.channel_id, "channel_id")
    since = parse_since(args.since) if getattr(args, "since", None) else None
    limit = _resolve_limit(args.limit, since is not None)
    # Never leave the direction to history()'s context-dependent default: it
    # flips to oldest-first as soon as ``after`` is passed.
    oldest_first = since is not None

    async def action(client: object) -> list[dict[str, object]]:
        channel = await client.fetch_channel(channel_id)
        history = channel.history(limit=limit, after=since, oldest_first=oldest_first)
        collected = [m async for m in history]
        if not oldest_first:  # we asked for newest-first; emit oldest-first
            collected.reverse()
        return [_message_dict(m) for m in collected]

    messages = discord_client.run(action)
    window = _window_signal(since, limit, len(messages))
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result(
            {"channel_id": str(channel_id), "messages": messages, "window": window},
            json_mode=True,
        )
    else:
        lines = [f"{m['id']}  {m['author']['name']}: {m['content']}" for m in messages]
        emit_result("\n".join(lines) if lines else "(no messages)", json_mode=False)
        if window["stopped_by"] == _STOPPED_BY_LIMIT:
            emit_diagnostic(
                f"window not fully covered: stopped at --limit {limit}; "
                "raise or drop --limit, or narrow --since"
            )
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
        "--since",
        metavar="WHEN",
        help=(
            "Read every message newer than WHEN (pages past the 100-message cap). "
            "An ISO 8601 timestamp with a UTC offset, a date 'YYYY-MM-DD' (midnight "
            "UTC), or a duration '<N><unit>' with h=hours, d=days, w=weeks, m=months."
        ),
    )
    pm.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            f"How many messages to read ({_LIMIT_MIN}-{_LIMIT_MAX}, default "
            f"{_LIMIT_DEFAULT}). With --since it is a safety ceiling on the walk "
            "and is not capped at 100."
        ),
    )
    add_json(pm)
    pm.set_defaults(func=cmd_channel_messages)

    ov = noun_sub.add_parser("overview", help="Describe the channel noun.")
    add_json(ov)
    ov.set_defaults(func=cmd_channel_overview)

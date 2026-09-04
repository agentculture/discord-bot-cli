"""``discord-bot-cli user`` — look up one or more Discord users.

Verbs:

* ``user get <user_id> [<user_id> ...] [--ids-file <path>|-]`` — fetch public
  profile fields for a batch of users.
* ``user overview`` — describe this noun.

All Discord I/O routes through :func:`discord_bot_cli.discord_client.run`.

``user get`` is a **batch** verb: every id supplied — positional args and/or
``--ids-file`` lines — resolves inside a single ``discord_client.run`` session
(one login, one close; see ``discord_client.py``'s one-shot contract). Ids are
resolved **sequentially, in input order**, and that order is a guarantee: the
output (both ``--json`` and text) lists results in the same order the ids were
given, positional ids first, then ``--ids-file`` lines. Resolution is not
parallelised with ``asyncio.gather`` because that would require buffering to
restore order anyway — a plain loop already gives ordered results for free.

``--json`` always emits an array, even for a single id — this is a deliberate
breaking change from the prior single-id object payload. A per-id
``NotFound``/``Forbidden`` failure does **not** fail the batch: it is caught
inside the action loop (never left to propagate out to
``discord_client.run``, which would map it to a ``CliError`` and abort every
id) and recorded as an ``{id, error, remediation}`` entry in the same
position. The process still exits 0 — an unresolvable id is data, not a CLI
failure, so a bad id in a 200-id scan doesn't turn the whole run red.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from discord_bot_cli import discord_client
from discord_bot_cli.cli._commands._discord_common import add_json, emit_noun_overview
from discord_bot_cli.cli._errors import EXIT_USER_ERROR, CliError
from discord_bot_cli.cli._output import emit_result

_VERBS = [
    "user get <user_id> [<user_id> ...] [--ids-file <path>|-] — fetch one or more "
    "users' public profiles, in input order (always a JSON array with --json)",
    "user overview — describe this noun (this command)",
]


def _read_ids_file(path: str) -> list[str]:
    if path == "-":
        content = sys.stdin.read()
    else:
        try:
            content = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(
                code=EXIT_USER_ERROR,
                message=f"cannot read --ids-file {path!r}: {exc}",
                remediation="check the path is correct and readable, or pass '-' for stdin",
            ) from exc
    return [line.strip() for line in content.splitlines() if line.strip()]


def _collect_ids(args: argparse.Namespace) -> list[int]:
    raw: list[str] = list(getattr(args, "user_id", None) or [])
    ids_file = getattr(args, "ids_file", None)
    if ids_file:
        raw.extend(_read_ids_file(ids_file))
    if not raw:
        raise CliError(
            code=EXIT_USER_ERROR,
            message="no user ids given",
            remediation="pass one or more user ids, or --ids-file <path|->",
        )
    return [discord_client.parse_id(value, "user_id") for value in raw]


def _error_entry(user_id: int, exc: BaseException) -> dict[str, object]:
    text = getattr(exc, "text", "") or str(exc)
    return {
        "id": str(user_id),
        "error": text,
        "remediation": "check the id is correct and visible to the bot",
    }


def _format_entry(entry: dict[str, object]) -> str:
    if "error" in entry:
        return f"{entry['id']}  error: {entry['error']}"
    return (
        f"{entry['id']}  {entry['username']} "
        f"(global_name={entry['global_name']}, bot={entry['bot']})"
    )


def cmd_user_get(args: argparse.Namespace) -> int:
    ids = _collect_ids(args)
    json_mode = bool(getattr(args, "json", False))

    async def action(client: object) -> list[dict[str, object]]:
        # Lazy import: discord_client.run() has already required the extra by
        # the time action() runs, so this is safe and keeps the runtime
        # package dependency-free (see discord_client.require_discord()).
        import discord  # noqa: PLC0415  (lazy import preserves zero runtime deps)

        results: list[dict[str, object]] = []
        for user_id in ids:
            try:
                user = await client.fetch_user(user_id)
            except (discord.NotFound, discord.Forbidden) as exc:
                # Caught HERE, inside the loop: letting these propagate out of
                # action() would have discord_client.run() map them to a
                # CliError and fail the WHOLE batch, which criterion 4 forbids.
                results.append(_error_entry(user_id, exc))
                continue
            results.append(
                {
                    "id": str(user.id),
                    "username": user.name,
                    "global_name": getattr(user, "global_name", None),
                    "bot": bool(getattr(user, "bot", False)),
                }
            )
        return results

    result: list[dict[str, Any]] = discord_client.run(action)
    if json_mode:
        emit_result(result, json_mode=True)
    else:
        emit_result("\n".join(_format_entry(entry) for entry in result), json_mode=False)
    return 0


def cmd_user_overview(args: argparse.Namespace) -> int:
    emit_noun_overview("user", _VERBS, json_mode=bool(getattr(args, "json", False)))
    return 0


def _no_verb(args: argparse.Namespace) -> int:
    return cmd_user_overview(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("user", help="Look up one or more Discord users.")
    add_json(p)
    p.set_defaults(func=_no_verb, json=False)
    noun_sub = p.add_subparsers(dest="user_command", parser_class=type(p))

    pg = noun_sub.add_parser("get", help="Fetch public profile(s) for one or more users.")
    pg.add_argument(
        "user_id",
        nargs="*",
        help="Numeric user id(s). One or more; combine with --ids-file if given.",
    )
    pg.add_argument(
        "--ids-file",
        help="Read additional newline-delimited user ids from a file (or '-' for stdin).",
    )
    add_json(pg)
    pg.set_defaults(func=cmd_user_get)

    ov = noun_sub.add_parser("overview", help="Describe the user noun.")
    add_json(ov)
    ov.set_defaults(func=cmd_user_overview)

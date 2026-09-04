"""Shared ``--file`` attachment seam for the Discord verbs.

Discord verbs that post content (``message post``, ``message reply``, ...)
optionally attach files. This module is the single place that:

* registers the repeatable, order-preserving ``--file`` flag alongside an
  optional positional ``content`` (:func:`add_file_flag`);
* validates and opens local paths into ``discord.File`` objects
  (:func:`build_files`), lazily importing ``discord`` via
  :func:`discord_bot_cli.discord_client.require_discord` so the runtime stays
  dependency-free;
* enforces the "some content required" rule (:func:`require_content_or_files`);
* renders a message's attachments back out as a JSON-friendly payload
  (:func:`attachments_payload`).

Verified against discord.py 2.7.1: ``discord.File.__init__`` opens its ``fp``
*eagerly*, so a bad path raises the builtin ``OSError`` at construction time —
not a ``discord.DiscordException`` subclass — and
``Messageable.send``/``.reply`` raise the builtin ``ValueError`` when handed
more than 10 files. Neither is caught by
:func:`discord_bot_cli.discord_client.run`'s exception mapping, which only
maps ``discord.*`` exceptions. This module exists precisely to turn those
builtin exceptions into a :class:`CliError` *before* any network call is
attempted, so a user never sees a raw traceback.

There is deliberately **no** attachment size pre-flight here: only Discord
knows a guild's real per-file cap (it is boost-tier dependent), so an
oversized file surfaces as an HTTP 413 mapped elsewhere. Only the fixed,
documented 10-files-per-message limit is asserted client-side.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from discord_bot_cli.cli._errors import EXIT_USER_ERROR, CliError
from discord_bot_cli.discord_client import require_discord

_MAX_FILES = 10  # discord.py: Messageable.send/reply accept at most 10 files


def add_file_flag(parser: argparse.ArgumentParser) -> None:
    """Attach an optional ``content`` positional and a repeatable ``--file`` flag.

    ``--file`` may be passed multiple times; argparse's ``append`` action
    preserves the order the flags were given in, and :func:`build_files`
    builds ``discord.File`` objects in that same order.
    """
    parser.add_argument("content", nargs="?", default=None, help="Message text.")
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        metavar="PATH",
        help="Path to a local file to attach. Repeatable, up to 10 files.",
    )


def require_content_or_files(content: str | None, files: list[str]) -> None:
    """Raise a user error unless there's something to post.

    ``content`` may be omitted only when at least one ``--file`` was given —
    Discord allows a file-only message, but never an empty one.
    """
    if content is None and not files:
        raise CliError(
            code=EXIT_USER_ERROR,
            message="nothing to post: no content and no --file",
            remediation="pass message text, at least one --file, or both",
        )


def build_files(paths: list[str]) -> list[Any]:
    """Validate ``paths`` and open them into ``discord.File`` objects, in order.

    Every failure mode here is caught and re-raised as a :class:`CliError`
    *before* any login is attempted:

    * more than 10 paths — the fixed, documented Discord per-message limit;
    * a path that doesn't exist, isn't a regular file, or isn't readable.
    """
    if len(paths) > _MAX_FILES:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"too many attachments: {len(paths)} (Discord allows at most {_MAX_FILES})",
            remediation=f"pass at most {_MAX_FILES} --file flags",
        )

    for path in paths:
        _check_readable_file(path)

    discord = require_discord()

    files = []
    try:
        for path in paths:
            files.append(discord.File(path, filename=os.path.basename(path)))
    except OSError as exc:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"could not open attachment {path!r}: {exc}",
            remediation="check the path exists, is a regular file, and is readable",
        ) from exc
    return files


def _check_readable_file(path: str) -> None:
    """Raise a user error unless ``path`` is a readable regular file.

    ``os.stat``/``os.access`` are used only to prove the path is a readable
    regular file — never to inspect or gate on its size.
    """
    if not os.path.exists(path):
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"attachment not found: {path!r}",
            remediation="check the --file path is correct",
        )
    if os.path.isdir(path):
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"attachment is a directory, not a file: {path!r}",
            remediation="pass a path to a regular file",
        )
    if not os.path.isfile(path) or not os.access(path, os.R_OK):
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"attachment is not a readable file: {path!r}",
            remediation="check the path points to a regular, readable file",
        )


def attachments_payload(message: Any) -> list[dict[str, object]]:
    """Map ``message.attachments`` to a JSON-friendly list of dicts."""
    return [
        {
            "id": str(attachment.id),
            "filename": attachment.filename,
            "url": attachment.url,
            "size": attachment.size,
        }
        for attachment in message.attachments
    ]

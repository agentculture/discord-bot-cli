"""Discord transport seam — the single place that talks to discord.py.

Every Discord verb routes through :func:`run`: it loads the bot token, lazy
-imports discord.py (the optional ``[discord]`` extra), opens a REST session,
awaits a caller-supplied coroutine, and *always* closes the session. Library and
HTTP failures are mapped to :class:`CliError` so no traceback ever leaks and the
agent-first error contract holds.

Two invariants live here:

* **Zero runtime dependencies.** ``import discord`` happens inside
  :func:`require_discord`, never at module top level, so ``pyproject``'s
  ``dependencies = []`` stays true and a checkout without the extra still imports
  cleanly (a verb then exits ``2`` with an install hint).
* **One-shot, no daemon.** :func:`run` uses ``asyncio.run`` and closes the
  client in a ``finally`` — no gateway/HTTP connection is left open after a verb
  prints its result. discord.py is connected only long enough to log in over
  REST and perform the single action (``Intents.none()`` — the gateway is never
  subscribed to).

This module is the seam tests stub: monkeypatch ``discord_client.run`` to feed a
fake client and assert each verb maps to the expected discord.py call, with no
live token.
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Any, Awaitable, Callable, TypeVar

from discord_bot_cli.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, CliError

if TYPE_CHECKING:  # pragma: no cover - typing only
    import discord

TOKEN_ENV = "DISCORD_BOT_TOKEN"  # the env-var NAME we read the token from (not a secret)
_INSTALL_HINT = (
    "install the Discord extra: uv add 'discord-bot-cli[discord]' "
    "(or: pip install 'discord-bot-cli[discord]')"
)

T = TypeVar("T")


def require_token() -> str:
    """Return the bot token from the environment, or raise an env error.

    The token is read from ``DISCORD_BOT_TOKEN`` only — never a flag — so it
    cannot leak into shell history or a process list. The value is never echoed
    to stdout/stderr.
    """
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise CliError(
            code=EXIT_ENV_ERROR,
            message=f"{TOKEN_ENV} is not set",
            remediation=(f"export {TOKEN_ENV}=<your bot token> (read from the env, never a flag)"),
        )
    return token


def require_discord() -> Any:
    """Lazy-import and return the ``discord`` module, or raise an env error.

    Kept out of module scope on purpose: the runtime package must import with
    ``dependencies = []``. An absent extra becomes a clean ``EXIT_ENV_ERROR``
    with an install hint, not an ``ImportError`` traceback.
    """
    try:
        import discord  # noqa: PLC0415  (lazy import preserves zero runtime deps)
    except ImportError as exc:
        raise CliError(
            code=EXIT_ENV_ERROR,
            message="the discord.py library is not installed",
            remediation=_INSTALL_HINT,
        ) from exc
    return discord


def parse_id(value: str, label: str) -> int:
    """Parse a Discord snowflake id, raising a user error with a hint on garbage."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"invalid {label}: {value!r} (expected a numeric Discord id)",
            remediation=f"pass a numeric {label} (a Discord snowflake, e.g. 123456789012345678)",
        ) from exc


def run(action: Callable[["discord.Client"], Awaitable[T]]) -> T:
    """Run a one-shot Discord action: login, await ``action(client)``, close.

    ``action`` is an async callable that receives a logged-in ``discord.Client``
    and returns a JSON-serialisable result. The client is always closed, so no
    connection survives the call (the one-shot, no-daemon contract).
    """
    token = require_token()
    discord = require_discord()
    return asyncio.run(_run_async(discord, token, action))


async def _run_async(
    discord: Any,
    token: str,
    action: Callable[["discord.Client"], Awaitable[T]],
) -> T:
    # Intents are a gateway concern; REST verbs need none. Intents.none() keeps
    # the client minimal and dodges privileged-intent errors.
    client = discord.Client(intents=discord.Intents.none())
    try:
        await client.login(token)
        return await action(client)
    except CliError:
        raise
    except discord.LoginFailure as exc:
        raise CliError(
            code=EXIT_ENV_ERROR,
            message="Discord rejected the bot token",
            remediation=f"check {TOKEN_ENV} holds a valid bot token",
        ) from exc
    except discord.Forbidden as exc:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"Discord forbade the request: {_http_text(exc)}",
            remediation="the bot lacks permission, or is not in that guild/channel",
        ) from exc
    except discord.NotFound as exc:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"not found: {_http_text(exc)}",
            remediation="check the id is correct and visible to the bot",
        ) from exc
    except discord.HTTPException as exc:
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"Discord API error ({getattr(exc, 'status', '?')}): {_http_text(exc)}",
            remediation="see https://discord.com/developers/docs/topics/opcodes-and-status-codes",
        ) from exc
    except discord.DiscordException as exc:  # catch-all so nothing leaks
        raise CliError(
            code=EXIT_USER_ERROR,
            message=f"Discord error: {exc}",
            remediation="re-run with valid ids and a bot that has access",
        ) from exc
    finally:
        await client.close()


def _http_text(exc: Any) -> str:
    """Best-effort human text from a discord.py HTTP exception."""
    return getattr(exc, "text", "") or str(exc)

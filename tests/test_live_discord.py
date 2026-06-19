"""Live tests against the real Discord API — opt-in, skipped by default.

Unlike the rest of the suite (which stubs the transport seam via ``fake_discord``
and needs no token or network), these tests drive the **real**
``discord_client.run`` → discord.py → Discord REST path. They are **doubly
gated** so a routine ``pytest`` run never logs in or posts, even on a machine
that happens to have ``DISCORD_BOT_TOKEN`` exported:

1. ``DISCORD_LIVE_TESTS`` must be truthy (the explicit opt-in switch), **and**
2. ``DISCORD_BOT_TOKEN`` must be set.

Each individual test additionally skips unless the id it needs is provided:

* ``DISCORD_TEST_GUILD_ID``   — a guild the bot is in (``channel list``)
* ``DISCORD_TEST_CHANNEL_ID`` — a text channel the bot can read **and** write
  (``channel messages`` + the whole write chain). The write tests POST real
  messages here, so point it at a throwaway/sandbox channel.
* ``DISCORD_TEST_USER_ID``    — any user id (``user get``); the bot's own id works.

Run them locally with::

    DISCORD_LIVE_TESTS=1 \\
    DISCORD_TEST_GUILD_ID=...  DISCORD_TEST_CHANNEL_ID=...  DISCORD_TEST_USER_ID=... \\
    uv run pytest -m live -v

The default suite deselects them implicitly (they self-skip) and CI runs them
from a dedicated ``live-tests`` workflow that injects the token as a secret.

There is no ``delete`` verb yet, so the write chain leaves its test messages in
the channel — another reason the channel should be a sandbox.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest

from discord_bot_cli.cli import main


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


_LIVE = _flag("DISCORD_LIVE_TESTS") and bool(_env("DISCORD_BOT_TOKEN"))
_GUILD = _env("DISCORD_TEST_GUILD_ID")
_CHANNEL = _env("DISCORD_TEST_CHANNEL_ID")
_USER = _env("DISCORD_TEST_USER_ID")

# Whole module is live + skipped unless the opt-in switch and a token are present.
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not _LIVE,
        reason="set DISCORD_LIVE_TESTS=1 and DISCORD_BOT_TOKEN to run live Discord tests",
    ),
]

_needs_guild = pytest.mark.skipif(not _GUILD, reason="set DISCORD_TEST_GUILD_ID")
_needs_channel = pytest.mark.skipif(not _CHANNEL, reason="set DISCORD_TEST_CHANNEL_ID")
_needs_user = pytest.mark.skipif(not _USER, reason="set DISCORD_TEST_USER_ID")


def _run(args: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict]:
    """Invoke the CLI with ``--json`` and return ``(exit_code, parsed_stdout)``.

    Errors print JSON to *stderr* (the agent-first contract), so on a non-zero
    exit we parse stderr instead — letting a test assert the live error mapping.
    """
    rc = main([*args, "--json"])
    captured = capsys.readouterr()
    stream = captured.out if rc == 0 else captured.err
    payload = json.loads(stream) if stream.strip() else {}
    return rc, payload


@_needs_user
def test_live_user_get(capsys: pytest.CaptureFixture[str]) -> None:
    rc, payload = _run(["user", "get", _USER], capsys)
    assert rc == 0, payload
    assert payload["id"] == _USER
    assert "username" in payload


@_needs_guild
def test_live_channel_list(capsys: pytest.CaptureFixture[str]) -> None:
    rc, payload = _run(["channel", "list", _GUILD], capsys)
    assert rc == 0, payload
    assert payload["guild_id"] == _GUILD
    assert isinstance(payload["channels"], list) and payload["channels"]
    for ch in payload["channels"]:
        assert {"id", "name", "type"} <= ch.keys()


@_needs_channel
def test_live_channel_messages(capsys: pytest.CaptureFixture[str]) -> None:
    rc, payload = _run(["channel", "messages", _CHANNEL, "--limit", "5"], capsys)
    assert rc == 0, payload
    assert isinstance(payload["messages"], list)  # may legitimately be empty


@_needs_channel
def test_live_write_chain(capsys: pytest.CaptureFixture[str]) -> None:
    """post → reply → react → thread create → thread post, composing on each id.

    Posts real messages to ``DISCORD_TEST_CHANNEL_ID`` (a sandbox channel).
    """
    tag = uuid.uuid4().hex[:8]

    rc, posted = _run(
        ["message", "post", _CHANNEL, f"discord-bot-cli live test {tag} — post. Safe to delete."],
        capsys,
    )
    assert rc == 0, posted
    assert posted["id"] and posted["channel_id"] == _CHANNEL

    rc, reply = _run(
        ["message", "reply", _CHANNEL, posted["id"], f"live test {tag} — reply"], capsys
    )
    assert rc == 0, reply
    assert reply["in_reply_to"] == posted["id"]

    rc, reacted = _run(["message", "react", _CHANNEL, posted["id"], "✅"], capsys)
    assert rc == 0, reacted
    assert reacted["reacted"] is True

    rc, thread = _run(
        ["thread", "create", _CHANNEL, "--name", f"live test {tag}", "--message", posted["id"]],
        capsys,
    )
    assert rc == 0, thread
    assert thread["anchored_to"] == posted["id"]

    rc, in_thread = _run(["thread", "post", thread["id"], f"live test {tag} — in-thread"], capsys)
    assert rc == 0, in_thread
    assert in_thread["thread_id"] == thread["id"]


@_needs_guild
def test_live_unknown_guild_is_user_error(capsys: pytest.CaptureFixture[str]) -> None:
    """A real but bogus guild id maps to a clean exit-1 error, not a traceback."""
    rc, payload = _run(["channel", "list", "1"], capsys)
    assert rc == 1, payload
    assert payload.get("message")  # structured error body, not a stack trace

"""End-to-end flow over the stubbed seam: each verb maps to its discord.py call.

Walks the success-signal path — channel list -> messages -> post -> reply ->
react -> thread create -> thread post -> user get — asserting the verb→library
mapping with no live token (the seam is stubbed by the ``fake_discord``
fixture).
"""

from __future__ import annotations

import json

import pytest

from discord_bot_cli.cli import main
from tests.conftest import FakeClient


def _run(args: list[str], capsys: pytest.CaptureFixture[str]) -> dict:
    rc = main([*args, "--json"])
    assert rc == 0, f"{' '.join(args)} exited {rc}"
    return json.loads(capsys.readouterr().out)


def test_full_compose_flow(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    # discover where to act
    channels = _run(["channel", "list", "777"], capsys)["channels"]
    assert channels

    msgs = _run(["channel", "messages", "555", "--limit", "2"], capsys)["messages"]
    assert msgs

    # write, then compose on the returned id
    posted = _run(["message", "post", "555", "hello"], capsys)
    reply = _run(["message", "reply", "555", posted["id"], "re: hello"], capsys)
    assert reply["in_reply_to"] == posted["id"]
    _run(["message", "react", "555", posted["id"], "✅"], capsys)

    # threads
    thread = _run(["thread", "create", "555", "--name", "topic"], capsys)
    _run(["thread", "post", thread["id"], "in-thread"], capsys)

    # people
    user = _run(["user", "get", "42"], capsys)
    assert user["username"] == "alice"

    # every documented endpoint was exercised on the fake client
    client_methods = {name for name, *_ in fake_discord.calls}
    assert {"fetch_guild", "fetch_channel", "fetch_user"} <= client_methods
    channel_methods = {name for name, *_ in fake_discord.channel.calls}
    assert {"history", "send", "fetch_message", "create_thread"} <= channel_methods


def test_missing_extra_is_env_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Real run() path with discord.py hidden and a token present -> exit 2, hint.
    import sys

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setitem(sys.modules, "discord", None)
    rc = main(["user", "get", "42"])
    assert rc == 2
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "discord-bot-cli[discord]" in err

"""Tests for the ``channel`` noun (list, messages, overview)."""

from __future__ import annotations

import json

import pytest

from discord_bot_cli.cli import main
from tests.conftest import FakeClient


def test_channel_list_json(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["channel", "list", "777", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["guild_id"] == "777"
    assert [c["name"] for c in payload["channels"]] == ["general", "random"]
    assert ("fetch_guild", 777) in fake_discord.calls
    assert ("fetch_channels", None) in fake_discord.guild.calls


def test_channel_list_text(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["channel", "list", "777"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "general" in out and "random" in out


def test_channel_messages_oldest_first(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["channel", "messages", "555", "--limit", "3", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    # FakeChannel yields newest-first; the verb reverses to oldest-first.
    assert [m["content"] for m in payload["messages"]] == ["first", "second", "third"]
    assert ("fetch_channel", 555) in fake_discord.calls
    assert ("history", 3) in fake_discord.channel.calls


def test_channel_messages_limit_out_of_range(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["channel", "messages", "555", "--limit", "999"])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "hint:" in err


def test_channel_messages_bad_id(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["channel", "messages", "not-an-id"])
    assert rc == 1
    assert "hint:" in capsys.readouterr().err


def test_channel_overview(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["channel", "overview"])
    assert rc == 0
    assert "# discord-bot-cli channel" in capsys.readouterr().out


def test_channel_bare_prints_overview(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["channel"])
    assert rc == 0
    assert "# discord-bot-cli channel" in capsys.readouterr().out

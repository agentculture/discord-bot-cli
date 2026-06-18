"""Tests for the ``message`` noun (post, reply, react, overview)."""

from __future__ import annotations

import json

import pytest

from discord_bot_cli.cli import main
from tests.conftest import FakeClient


def test_message_post_returns_id(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["message", "post", "123", "hello world", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "999"  # the created message id, for composing
    assert payload["channel_id"] == "123"
    assert ("fetch_channel", 123) in fake_discord.calls
    assert ("send", "hello world") in fake_discord.channel.calls


def test_message_reply_sets_reference(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["message", "reply", "123", "456", "a reply", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["in_reply_to"] == "456"
    assert payload["id"] == "1000"
    assert ("fetch_message", 456) in fake_discord.channel.calls
    # reply() was called on the fetched target message
    assert ("reply", "a reply") in fake_discord.channel.last_fetched_message.calls


def test_message_react(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["message", "react", "123", "456", "👍", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"message_id": "456", "emoji": "👍", "reacted": True}
    assert ("add_reaction", "👍") in fake_discord.channel.last_fetched_message.calls


def test_message_post_text_mode(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["message", "post", "123", "hi"])
    assert rc == 0
    assert "posted message 999" in capsys.readouterr().out


def test_message_overview(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["message", "overview"])
    assert rc == 0
    assert "# discord-bot-cli message" in capsys.readouterr().out

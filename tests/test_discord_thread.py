"""Tests for the ``thread`` noun (create, post, overview)."""

from __future__ import annotations

import json

import pytest

from discord_bot_cli.cli import main
from tests.conftest import FakeClient


def test_thread_create_standalone(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["thread", "create", "123", "--name", "triage", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "triage"
    assert payload["anchored_to"] is None
    assert payload["id"] == "556"
    # standalone path creates a public thread on the channel
    assert ("create_thread", "triage", "public_thread") in fake_discord.channel.calls


def test_thread_create_anchored(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["thread", "create", "123", "--name", "from-msg", "--message", "456", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["anchored_to"] == "456"
    assert payload["id"] == "555"  # thread created off the fetched message
    assert ("fetch_message", 456) in fake_discord.channel.calls
    assert ("create_thread", "from-msg") in fake_discord.channel.last_fetched_message.calls


def test_thread_create_requires_name(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["thread", "create", "123"])
    assert exc.value.code == 1
    assert "hint:" in capsys.readouterr().err


def test_thread_post(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["thread", "post", "789", "first post", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["thread_id"] == "789"
    assert ("fetch_channel", 789) in fake_discord.calls
    assert ("send", "first post") in fake_discord.channel.calls


def test_thread_overview(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["thread", "overview"])
    assert rc == 0
    assert "# discord-bot-cli thread" in capsys.readouterr().out

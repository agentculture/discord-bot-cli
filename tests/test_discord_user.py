"""Tests for the ``user`` noun (get, overview)."""

from __future__ import annotations

import json

import pytest

from discord_bot_cli.cli import main
from tests.conftest import FakeClient


def test_user_get_json(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["user", "get", "42", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"id": "42", "username": "alice", "global_name": "Alice", "bot": False}
    assert ("fetch_user", 42) in fake_discord.calls


def test_user_get_text(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["user", "get", "42"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "alice" in out and "42" in out


def test_user_get_bad_id(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["user", "get", "nope"])
    assert rc == 1
    assert "hint:" in capsys.readouterr().err


def test_user_overview(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["user", "overview"])
    assert rc == 0
    assert "# discord-bot-cli user" in capsys.readouterr().out

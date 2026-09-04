"""Tests for the ``message`` noun (post, reply, react, overview)."""

from __future__ import annotations

import json

import pytest

from discord_bot_cli.cli import main
from tests.conftest import FakeAttachment, FakeClient


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


def _make_files(tmp_path, names: list[str]) -> list[str]:
    paths = []
    for name in names:
        p = tmp_path / name
        p.write_text(f"content of {name}")
        paths.append(str(p))
    return paths


def test_message_post_multiple_files_single_send(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str], tmp_path
) -> None:
    a, b = _make_files(tmp_path, ["a.png", "b.png"])
    rc = main(["message", "post", "123", "look", "--file", a, "--file", b, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "999"
    # exactly one send — no companion webhook call / second command
    assert len(fake_discord.channel.sent) == 1
    files = fake_discord.channel.last_files
    assert files is not None
    assert [f.filename for f in files] == ["a.png", "b.png"]  # order preserved


def test_message_post_file_only_no_content(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str], tmp_path
) -> None:
    (a,) = _make_files(tmp_path, ["only.txt"])
    rc = main(["message", "post", "123", "--file", a, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "999"
    assert fake_discord.channel.sent[-1]["content"] is None
    assert [f.filename for f in fake_discord.channel.last_files] == ["only.txt"]


def test_message_post_no_content_no_file_errors(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["message", "post", "123"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "hint:" in err


def test_message_post_bad_path_errors(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["message", "post", "123", "hi", "--file", "/nonexistent/path/whatever.png"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "not found" in err


def test_message_reply_with_files(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str], tmp_path
) -> None:
    (a,) = _make_files(tmp_path, ["reply.pdf"])
    rc = main(["message", "reply", "123", "456", "see attached", "--file", a, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "1000"
    assert payload["in_reply_to"] == "456"
    target = fake_discord.channel.last_fetched_message
    assert len(target.replies) == 1  # one invocation, one send
    assert [f.filename for f in target.last_files] == ["reply.pdf"]


def test_message_reply_file_only_no_content(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str], tmp_path
) -> None:
    (a,) = _make_files(tmp_path, ["only.txt"])
    rc = main(["message", "reply", "123", "456", "--file", a, "--json"])
    assert rc == 0
    target = fake_discord.channel.last_fetched_message
    assert target.replies[-1]["content"] is None


def test_message_reply_no_content_no_file_errors(fake_discord: FakeClient) -> None:
    rc = main(["message", "reply", "123", "456"])
    assert rc == 1


def test_message_post_json_includes_attachments(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str], tmp_path, monkeypatch
) -> None:
    """The ``attachments`` field mirrors ``message.attachments`` verbatim.

    Discord's fake ``send`` doesn't itself simulate the server round-trip that
    populates ``message.attachments`` (the returned FakeMessage carries none),
    so we wrap ``send`` here to stand in for that round-trip and assert the
    verb faithfully reads whatever attachments come back on the message.
    """
    (a,) = _make_files(tmp_path, ["pic.png"])
    channel = fake_discord.channel
    real_send = channel.send

    async def send_with_attachments(content=None, *, files=None):
        message = await real_send(content, files=files)
        message.attachments = [
            FakeAttachment(
                777,
                filename="pic.png",
                url="https://cdn.discordapp.com/attachments/123/777/pic.png",
                size=42,
            )
        ]
        return message

    monkeypatch.setattr(channel, "send", send_with_attachments)

    rc = main(["message", "post", "123", "--file", a, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "999"
    assert payload["attachments"] == [
        {
            "id": "777",
            "filename": "pic.png",
            "url": "https://cdn.discordapp.com/attachments/123/777/pic.png",
            "size": 42,
        }
    ]


def test_message_post_json_attachments_empty_without_files(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["message", "post", "123", "hello", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["attachments"] == []


def test_message_post_text_only_still_parses(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """The existing positional form keeps working after ``nargs='?'``."""
    rc = main(["message", "post", "123", "plain text"])
    assert rc == 0
    assert ("send", "plain text") in fake_discord.channel.calls

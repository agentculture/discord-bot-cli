"""Tests for the shared test doubles themselves (``tests/conftest.py``).

The fakes are the substrate every Discord verb test stands on. If they encode
the wrong discord.py semantics, downstream tests pass against a fake that lies
and a real bug ships green. These tests pin the semantics that were verified
against discord.py 2.7.1 — most importantly ``Messageable.history``'s
``oldest_first`` default, which *flips* depending on whether ``after`` was
given (``discord/abc.py``: ``reverse = after is not None`` when
``oldest_first is None``).
"""

from __future__ import annotations

import asyncio
import datetime as _dt
from typing import Any

import pytest

from tests.conftest import FakeAttachment, FakeClient, FakeMessage, FakeUser, discord_errors


def _drain(aiter: Any) -> list[Any]:
    async def go() -> list[Any]:
        return [m async for m in aiter]

    return asyncio.run(go())


def _contents(channel: Any, **kwargs: Any) -> list[str]:
    return [m.content for m in _drain(channel.history(**kwargs))]


# --- criterion 1: files= on send/reply -------------------------------------


def test_channel_send_accepts_content_only() -> None:
    channel = FakeClient().channel
    msg = asyncio.run(channel.send("hello"))
    assert msg.content == "hello"
    # the legacy 2-tuple recording that pre-existing tests assert on
    assert ("send", "hello") in channel.calls
    assert channel.sent[-1] == {"content": "hello", "files": None}
    assert channel.last_files is None


def test_channel_send_records_files_kwarg() -> None:
    channel = FakeClient().channel
    files = [object(), object()]
    asyncio.run(channel.send("caption", files=files))
    assert ("send", "caption") in channel.calls
    assert channel.sent[-1]["files"] == files
    assert channel.last_files == files


def test_message_reply_accepts_content_only_and_files() -> None:
    msg = FakeMessage(7, author=FakeUser(1, name="bob"), content="x")
    asyncio.run(msg.reply("plain"))
    assert ("reply", "plain") in msg.calls
    assert msg.replies[-1] == {"content": "plain", "files": None}

    files = [object()]
    asyncio.run(msg.reply("with file", files=files))
    assert ("reply", "with file") in msg.calls
    assert msg.replies[-1]["files"] == files
    assert msg.last_files == files


def test_thread_send_accepts_files() -> None:
    channel = FakeClient().channel
    thread = asyncio.run(channel.create_thread(name="t"))
    files = [object()]
    asyncio.run(thread.send("hi", files=files))
    assert thread.sent[-1] == {"content": "hi", "files": files}


def test_send_does_not_silently_accept_more_than_ten_files() -> None:
    """discord.py raises a builtin ``ValueError`` for >10 files; so must the fake."""
    channel = FakeClient().channel
    send = channel.send("too many", files=[object()] * 11)
    with pytest.raises(ValueError):
        asyncio.run(send)


# --- criterion 2: attachments ----------------------------------------------


def test_message_exposes_attachments() -> None:
    att = FakeAttachment(1, filename="a.png", url="https://cdn/a.png", size=12)
    msg = FakeMessage(7, author=FakeUser(1, name="bob"), content="x", attachments=[att])
    (got,) = msg.attachments
    assert (got.id, got.filename, got.url, got.size) == (1, "a.png", "https://cdn/a.png", 12)


def test_message_attachments_default_empty() -> None:
    msg = FakeMessage(7, author=FakeUser(1, name="bob"), content="x")
    assert msg.attachments == []


def test_history_fixture_has_an_attachment_to_exercise() -> None:
    channel = FakeClient().channel
    with_atts = [m for m in channel.history_messages if m.attachments]
    assert with_atts, "at least one fixture message must carry an attachment"
    att = with_atts[0].attachments[0]
    for field in ("id", "filename", "url", "size"):
        assert getattr(att, field) is not None


# --- criterion 3: history(after=, limit=None, oldest_first=) ---------------


def test_history_defaults_to_newest_first() -> None:
    channel = FakeClient().channel
    assert _contents(channel) == ["third", "second", "first"]


def test_history_with_after_flips_default_to_oldest_first() -> None:
    """``oldest_first`` defaults to True when ``after`` is given. The trap."""
    channel = FakeClient().channel
    assert _contents(channel, after=_snowflake(0)) == ["first", "second", "third"]


def test_history_explicit_oldest_first_overrides_both_defaults() -> None:
    channel = FakeClient().channel
    assert _contents(channel, oldest_first=True) == ["first", "second", "third"]
    assert _contents(channel, after=_snowflake(0), oldest_first=False) == [
        "third",
        "second",
        "first",
    ]


def test_history_after_is_exclusive_by_snowflake() -> None:
    channel = FakeClient().channel
    assert _contents(channel, after=_snowflake(1)) == ["second", "third"]
    assert _contents(channel, after=_snowflake(3)) == []


def test_history_after_accepts_a_datetime() -> None:
    channel = FakeClient().channel
    first = [m for m in channel.history_messages if m.content == "first"][0]
    assert _contents(channel, after=first.created_at) == ["second", "third"]


def test_history_limit_none_means_everything() -> None:
    channel = FakeClient().channel
    assert len(_contents(channel, limit=None)) == len(channel.history_messages)


def test_history_limit_truncates_in_yield_order() -> None:
    channel = FakeClient().channel
    assert _contents(channel, limit=2) == ["third", "second"]
    assert _contents(channel, after=_snowflake(0), limit=2) == ["first", "second"]


def test_history_records_its_arguments() -> None:
    channel = FakeClient().channel
    _drain(channel.history(limit=2, after=_snowflake(1), oldest_first=False))
    assert ("history", 2) in channel.calls  # legacy 2-tuple recording
    recorded = channel.history_calls[-1]
    assert recorded["limit"] == 2
    assert recorded["oldest_first"] is False
    assert getattr(recorded["after"], "id", None) == 1


def _snowflake(mid: int) -> Any:
    """A Snowflake-ish object: anything with an ``.id``."""
    return type("Obj", (), {"id": mid})()


# --- criterion 4: per-id fetch_user failures -------------------------------


def test_fetch_user_returns_a_user_per_id() -> None:
    client = FakeClient()
    assert asyncio.run(client.fetch_user(42)).name == "alice"  # the seeded default
    other = asyncio.run(client.fetch_user(99))
    assert other.id == 99
    assert ("fetch_user", 99) in client.calls


def test_fetch_user_can_be_told_to_raise_not_found() -> None:
    not_found, _ = discord_errors()
    client = FakeClient()
    client.fail_user(99, "not_found")
    lookup = client.fetch_user(99)
    with pytest.raises(not_found):
        asyncio.run(lookup)
    # other ids still resolve — that is what makes per-id batch tolerance testable
    assert asyncio.run(client.fetch_user(42)).name == "alice"


def test_fetch_user_can_be_told_to_raise_forbidden() -> None:
    _, forbidden = discord_errors()
    client = FakeClient()
    client.fail_user(7, "forbidden")
    lookup = client.fetch_user(7)
    with pytest.raises(forbidden):
        asyncio.run(lookup)


def test_fail_user_accepts_an_explicit_exception() -> None:
    client = FakeClient()
    boom = RuntimeError("boom")
    client.fail_user(5, boom)
    lookup = client.fetch_user(5)
    with pytest.raises(RuntimeError):
        asyncio.run(lookup)


def test_discord_errors_are_the_real_types_when_installed() -> None:
    not_found, forbidden = discord_errors()
    discord = pytest.importorskip("discord")
    assert not_found is discord.NotFound
    assert forbidden is discord.Forbidden


# --- sanity: fixture data shape --------------------------------------------


def test_history_messages_have_distinct_increasing_timestamps() -> None:
    channel = FakeClient().channel
    by_id = sorted(channel.history_messages, key=lambda m: m.id)
    stamps = [m.created_at for m in by_id]
    assert all(isinstance(s, _dt.datetime) for s in stamps)
    assert stamps == sorted(stamps)
    assert len(set(stamps)) == len(stamps)

"""Shared test doubles for the Discord verbs.

The verbs route all Discord I/O through
:func:`discord_bot_cli.discord_client.run`. Tests stub that one seam with
:func:`fake_discord`, which runs the verb's action coroutine against a recording
:class:`FakeClient` — so every test asserts the verb→discord.py mapping with no
live token and no network.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
from types import SimpleNamespace
from typing import Any

import pytest


class _AsyncIter:
    """Minimal async iterator for faking ``channel.history(...)``."""

    def __init__(self, items: list[Any]) -> None:
        self._items = list(items)

    def __aiter__(self) -> "_AsyncIter":
        return self

    async def __anext__(self) -> Any:
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


class FakeMessage:
    def __init__(self, mid: int, *, author: "FakeUser", content: str) -> None:
        self.id = mid
        self.author = author
        self.content = content
        self.created_at = _dt.datetime(2026, 6, 18, 12, 0, 0, tzinfo=_dt.timezone.utc)
        self.calls: list[tuple[str, Any]] = []

    async def reply(self, content: str) -> "FakeMessage":
        self.calls.append(("reply", content))
        return FakeMessage(1000, author=self.author, content=content)

    async def add_reaction(self, emoji: str) -> None:
        self.calls.append(("add_reaction", emoji))

    async def create_thread(self, *, name: str) -> "FakeThread":
        self.calls.append(("create_thread", name))
        return FakeThread(555, name=name)


class FakeThread:
    def __init__(self, tid: int, *, name: str) -> None:
        self.id = tid
        self.name = name

    async def send(self, content: str) -> FakeMessage:
        return FakeMessage(1002, author=FakeUser(1, name="bot"), content=content)


class FakeUser:
    def __init__(self, uid: int, *, name: str, global_name: str | None = None, bot: bool = False):
        self.id = uid
        self.name = name
        self.global_name = global_name
        self.bot = bot


class FakeChannel:
    """Doubles as a text channel and a thread (a Messageable)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.history_messages = [
            FakeMessage(3, author=FakeUser(20, name="carol"), content="third"),
            FakeMessage(2, author=FakeUser(10, name="bob"), content="second"),
            FakeMessage(1, author=FakeUser(10, name="bob"), content="first"),
        ]  # newest-first, like discord.py

    def history(self, *, limit: int) -> _AsyncIter:
        self.calls.append(("history", limit))
        return _AsyncIter(self.history_messages[:limit])

    async def send(self, content: str) -> FakeMessage:
        self.calls.append(("send", content))
        return FakeMessage(999, author=FakeUser(1, name="bot"), content=content)

    async def fetch_message(self, mid: int) -> FakeMessage:
        self.calls.append(("fetch_message", mid))
        msg = FakeMessage(mid, author=FakeUser(10, name="bob"), content="target")
        self.last_fetched_message = msg
        return msg

    async def create_thread(self, *, name: str, type: Any = None) -> FakeThread:  # noqa: A002
        self.calls.append(("create_thread", name, getattr(type, "name", type)))
        return FakeThread(556, name=name)


class FakeGuild:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def fetch_channels(self) -> list[Any]:
        self.calls.append(("fetch_channels", None))
        return [
            SimpleNamespace(id=11, name="general", type=SimpleNamespace(name="text")),
            SimpleNamespace(id=12, name="random", type=SimpleNamespace(name="text")),
        ]


class FakeClient:
    """Recording fake passed to verb action coroutines."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.closed = False
        self.guild = FakeGuild()
        self.channel = FakeChannel()
        self.user = FakeUser(42, name="alice", global_name="Alice", bot=False)

    async def fetch_guild(self, gid: int) -> FakeGuild:
        self.calls.append(("fetch_guild", gid))
        return self.guild

    async def fetch_channel(self, cid: int) -> FakeChannel:
        self.calls.append(("fetch_channel", cid))
        return self.channel

    async def fetch_user(self, uid: int) -> FakeUser:
        self.calls.append(("fetch_user", uid))
        return self.user


@pytest.fixture
def fake_discord(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    """Stub ``discord_client.run`` to execute the action against a FakeClient.

    Returns the FakeClient so a test can inspect ``.calls`` (and the nested
    channel/guild call logs) to assert the verb→discord.py mapping.
    """
    client = FakeClient()

    def fake_run(action: Any) -> Any:
        return asyncio.run(action(client))

    monkeypatch.setattr("discord_bot_cli.discord_client.run", fake_run)
    return client

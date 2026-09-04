"""Shared test doubles for the Discord verbs.

The verbs route all Discord I/O through
:func:`discord_bot_cli.discord_client.run`. Tests stub that one seam with
:func:`fake_discord`, which runs the verb's action coroutine against a recording
:class:`FakeClient` — so every test asserts the verb→discord.py mapping with no
live token and no network.

**The fakes must not lie.** They encode semantics verified against the installed
discord.py (2.7.1), not what a caller might naively expect:

* ``Messageable.history``'s ``oldest_first`` defaults to ``True`` when ``after``
  is given and ``False`` otherwise (``discord/abc.py``:
  ``reverse = after is not None`` when ``oldest_first is None``). An explicit
  ``oldest_first=`` overrides both.
* ``history(limit=None)`` means "every message", not "no messages".
* ``after=`` is *exclusive* and accepts either a ``datetime`` or a Snowflake-ish
  object (anything with an ``.id``); an ``int`` is accepted too.
* ``Messageable.send`` takes at most 10 ``files=``; more raises the builtin
  ``ValueError`` — not a discord exception.

**Recording conventions.** ``calls`` keeps the historical ``(name, arg)`` tuples
(``("send", content)``, ``("history", limit)``, …) so tests can keep asserting
membership. Richer detail that does not fit a 2-tuple lives alongside it:
``FakeChannel.sent`` / ``FakeThread.sent`` / ``FakeMessage.replies`` (lists of
``{"content", "files"}`` dicts, plus ``last_files``) and
``FakeChannel.history_calls`` (a dict per call).

There is no module-scope ``import discord`` here — the runtime package is
dependency-free and the suite must import without the extra. :func:`discord_errors`
lazy-imports the real ``discord.NotFound`` / ``discord.Forbidden`` when available
and falls back to local stand-ins otherwise.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
from types import SimpleNamespace
from typing import Any

import pytest

_MAX_FILES = 10  # discord.py: Messageable.send accepts at most 10 files
_EPOCH = _dt.datetime(2026, 6, 18, 12, 0, 0, tzinfo=_dt.timezone.utc)


# --------------------------------------------------------------------------
# Discord exception types (lazy — no module-scope ``import discord``)
# --------------------------------------------------------------------------


class _StandInNotFound(Exception):
    """Used only when discord.py is not installed."""


class _StandInForbidden(Exception):
    """Used only when discord.py is not installed."""


_errors_cache: tuple[type[BaseException], type[BaseException]] | None = None


def discord_errors() -> tuple[type[BaseException], type[BaseException]]:
    """Return ``(NotFound, Forbidden)`` — the real discord.py types if importable."""
    global _errors_cache
    if _errors_cache is None:
        try:
            import discord  # noqa: PLC0415 - deliberately lazy
        except ImportError:  # pragma: no cover - the extra is a dev dep in CI
            _errors_cache = (_StandInNotFound, _StandInForbidden)
        else:
            _errors_cache = (discord.NotFound, discord.Forbidden)
    return _errors_cache


def make_discord_error(kind: str, message: str = "") -> BaseException:
    """Build a real ``discord.NotFound``/``Forbidden`` instance (or a stand-in).

    ``kind`` is ``"not_found"`` or ``"forbidden"``. The real types are
    ``HTTPException`` subclasses and need a response object exposing ``.status``
    and ``.reason``; a ``SimpleNamespace`` satisfies that.
    """
    not_found, forbidden = discord_errors()
    if kind == "not_found":
        exc_type, status, reason = not_found, 404, "Not Found"
    elif kind == "forbidden":
        exc_type, status, reason = forbidden, 403, "Forbidden"
    else:  # pragma: no cover - programmer error in a test
        raise ValueError(f"unknown discord error kind: {kind!r}")
    if issubclass(exc_type, (_StandInNotFound, _StandInForbidden)):  # pragma: no cover
        return exc_type(message or reason)
    response = SimpleNamespace(status=status, reason=reason)
    return exc_type(response, message or reason)


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------


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


def _check_files(files: list[Any] | None) -> None:
    """Mirror discord.py: >10 files is a builtin ``ValueError``, not a discord error."""
    if files is not None and len(files) > _MAX_FILES:
        raise ValueError(f"files parameter must be a list of up to {_MAX_FILES} elements")


class FakeAttachment:
    """A ``discord.Attachment`` stand-in: the fields the verbs actually read."""

    def __init__(self, aid: int, *, filename: str, url: str, size: int) -> None:
        self.id = aid
        self.filename = filename
        self.url = url
        self.size = size


class FakeMessage:
    def __init__(
        self,
        mid: int,
        *,
        author: "FakeUser",
        content: str,
        created_at: _dt.datetime | None = None,
        attachments: list[FakeAttachment] | None = None,
    ) -> None:
        self.id = mid
        self.author = author
        self.content = content
        self.created_at = created_at if created_at is not None else _EPOCH
        self.attachments: list[FakeAttachment] = list(attachments or [])
        self.calls: list[tuple[str, Any]] = []
        self.replies: list[dict[str, Any]] = []
        self.last_files: list[Any] | None = None

    async def reply(self, content: str | None = None, *, files: list[Any] | None = None):
        _check_files(files)
        self.calls.append(("reply", content))
        self.replies.append({"content": content, "files": files})
        self.last_files = files
        return FakeMessage(1000, author=self.author, content=content or "")

    async def add_reaction(self, emoji: str) -> None:
        self.calls.append(("add_reaction", emoji))

    async def create_thread(self, *, name: str) -> "FakeThread":
        self.calls.append(("create_thread", name))
        return FakeThread(555, name=name)


class FakeThread:
    def __init__(self, tid: int, *, name: str) -> None:
        self.id = tid
        self.name = name
        self.calls: list[tuple[str, Any]] = []
        self.sent: list[dict[str, Any]] = []
        self.last_files: list[Any] | None = None

    async def send(self, content: str | None = None, *, files: list[Any] | None = None):
        _check_files(files)
        self.calls.append(("send", content))
        self.sent.append({"content": content, "files": files})
        self.last_files = files
        return FakeMessage(1002, author=FakeUser(1, name="bot"), content=content or "")


class FakeUser:
    def __init__(self, uid: int, *, name: str, global_name: str | None = None, bot: bool = False):
        self.id = uid
        self.name = name
        self.global_name = global_name
        self.bot = bot


def _after_excludes(message: FakeMessage, after: Any) -> bool:
    """``after`` is exclusive; it may be a datetime, a Snowflake-ish object, or an int."""
    if isinstance(after, _dt.datetime):
        return message.created_at <= after
    after_id = getattr(after, "id", after)
    return message.id <= int(after_id)


def _before_excludes(message: FakeMessage, before: Any) -> bool:
    if isinstance(before, _dt.datetime):
        return message.created_at >= before
    before_id = getattr(before, "id", before)
    return message.id >= int(before_id)


class FakeChannel:
    """Doubles as a text channel and a thread (a Messageable)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.sent: list[dict[str, Any]] = []
        self.last_files: list[Any] | None = None
        self.history_calls: list[dict[str, Any]] = []
        self.history_messages = [
            FakeMessage(
                3,
                author=FakeUser(20, name="carol"),
                content="third",
                created_at=_EPOCH + _dt.timedelta(minutes=3),
                attachments=[
                    FakeAttachment(
                        900,
                        filename="notes.txt",
                        url="https://cdn.discordapp.com/attachments/555/900/notes.txt",
                        size=1234,
                    )
                ],
            ),
            FakeMessage(
                2,
                author=FakeUser(10, name="bob"),
                content="second",
                created_at=_EPOCH + _dt.timedelta(minutes=2),
            ),
            FakeMessage(
                1,
                author=FakeUser(10, name="bob"),
                content="first",
                created_at=_EPOCH + _dt.timedelta(minutes=1),
            ),
        ]  # newest-first, like discord.py

    def history(
        self,
        *,
        limit: int | None = 100,
        before: Any = None,
        after: Any = None,
        around: Any = None,
        oldest_first: bool | None = None,
    ) -> _AsyncIter:
        self.calls.append(("history", limit))
        self.history_calls.append(
            {
                "limit": limit,
                "before": before,
                "after": after,
                "around": around,
                "oldest_first": oldest_first,
            }
        )
        # discord/abc.py: when oldest_first is unset the direction FLIPS on `after`.
        reverse = (after is not None) if oldest_first is None else bool(oldest_first)
        messages = [
            m
            for m in self.history_messages  # stored newest-first
            if not (after is not None and _after_excludes(m, after))
            and not (before is not None and _before_excludes(m, before))
        ]
        if reverse:
            messages = list(reversed(messages))  # oldest-first
        if limit is not None:  # limit=None means "everything"
            messages = messages[:limit]
        return _AsyncIter(messages)

    async def send(self, content: str | None = None, *, files: list[Any] | None = None):
        _check_files(files)
        self.calls.append(("send", content))
        self.sent.append({"content": content, "files": files})
        self.last_files = files
        return FakeMessage(999, author=FakeUser(1, name="bot"), content=content or "")

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
        self.run_kwargs: list[dict[str, Any]] = []
        self.closed = False
        self.guild = FakeGuild()
        self.channel = FakeChannel()
        self.user = FakeUser(42, name="alice", global_name="Alice", bot=False)
        # Per-id user registry + failure injection, so batch verbs can be tested
        # for per-id tolerance (one id 404s, the rest still resolve).
        self.users: dict[int, FakeUser] = {self.user.id: self.user}
        self.user_errors: dict[int, BaseException] = {}

    def add_user(self, user: FakeUser) -> FakeUser:
        self.users[user.id] = user
        return user

    def fail_user(self, uid: int, error: str | BaseException = "not_found") -> BaseException:
        """Make ``fetch_user(uid)`` raise.

        ``error`` is ``"not_found"`` / ``"forbidden"`` (built as the real
        discord.py exception) or an exception instance to raise verbatim.
        """
        exc = error if isinstance(error, BaseException) else make_discord_error(error)
        self.user_errors[uid] = exc
        return exc

    async def fetch_guild(self, gid: int) -> FakeGuild:
        self.calls.append(("fetch_guild", gid))
        return self.guild

    async def fetch_channel(self, cid: int) -> FakeChannel:
        self.calls.append(("fetch_channel", cid))
        return self.channel

    async def fetch_user(self, uid: int) -> FakeUser:
        self.calls.append(("fetch_user", uid))
        if uid in self.user_errors:
            raise self.user_errors[uid]
        if uid not in self.users:
            self.users[uid] = FakeUser(uid, name=f"user{uid}", global_name=None, bot=False)
        return self.users[uid]


@pytest.fixture
def fake_discord(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    """Stub ``discord_client.run`` to execute the action against a FakeClient.

    Returns the FakeClient so a test can inspect ``.calls`` (and the nested
    channel/guild call logs) to assert the verb→discord.py mapping.
    """
    client = FakeClient()

    def fake_run(action: Any, **kwargs: Any) -> Any:
        # Mirror the real ``run``'s keyword-only extras (e.g. ``upload_bytes``)
        # so a verb passing one is exercised rather than TypeError-ing here.
        client.run_kwargs.append(kwargs)
        return asyncio.run(action(client))

    monkeypatch.setattr("discord_bot_cli.discord_client.run", fake_run)
    return client

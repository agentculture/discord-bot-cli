"""Tests for the Discord transport seam (discord_bot_cli.discord_client)."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from discord_bot_cli import discord_client
from discord_bot_cli.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, CliError

# --- require_token --------------------------------------------------------


def test_require_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    with pytest.raises(CliError) as exc:
        discord_client.require_token()
    assert exc.value.code == EXIT_ENV_ERROR
    assert exc.value.remediation  # carries a hint


def test_require_token_blank_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "   ")
    with pytest.raises(CliError) as exc:
        discord_client.require_token()
    assert exc.value.code == EXIT_ENV_ERROR


def test_require_token_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "  secret-token  ")
    assert discord_client.require_token() == "secret-token"


def test_token_never_appears_in_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    with pytest.raises(CliError) as exc:
        discord_client.require_token()
    # the message/hint must not echo a token value
    assert "secret" not in (exc.value.message + exc.value.remediation)


# --- require_discord ------------------------------------------------------


def test_require_discord_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Hiding the module makes `import discord` raise ImportError.
    monkeypatch.setitem(sys.modules, "discord", None)
    with pytest.raises(CliError) as exc:
        discord_client.require_discord()
    assert exc.value.code == EXIT_ENV_ERROR
    assert "discord-bot-cli[discord]" in exc.value.remediation


def test_require_discord_present() -> None:
    mod = discord_client.require_discord()
    assert hasattr(mod, "Client")


# --- parse_id -------------------------------------------------------------


def test_parse_id_ok() -> None:
    assert discord_client.parse_id("123456789", "channel_id") == 123456789


def test_parse_id_bad() -> None:
    with pytest.raises(CliError) as exc:
        discord_client.parse_id("not-a-number", "channel_id")
    assert exc.value.code == EXIT_USER_ERROR
    assert "channel_id" in exc.value.message


# --- run / _run_async -----------------------------------------------------


class _FakeClient:
    last: "_FakeClient | None" = None

    def __init__(self, *, intents: object) -> None:
        self.closed = False
        self.logged_in = False
        _FakeClient.last = self

    async def login(self, token: str) -> None:
        self.logged_in = True

    async def close(self) -> None:
        self.closed = True


class _DiscordException(Exception):
    pass


class _HTTPException(_DiscordException):
    def __init__(self, text: str = "", status: int = 400) -> None:
        super().__init__(text)
        self.text = text
        self.status = status


class _Forbidden(_HTTPException):
    pass


class _NotFound(_HTTPException):
    pass


class _LoginFailure(_DiscordException):
    pass


def _fake_discord_module() -> SimpleNamespace:
    return SimpleNamespace(
        Client=_FakeClient,
        Intents=SimpleNamespace(none=lambda: object()),
        DiscordException=_DiscordException,
        HTTPException=_HTTPException,
        Forbidden=_Forbidden,
        NotFound=_NotFound,
        LoginFailure=_LoginFailure,
    )


@pytest.fixture
def patched_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setattr(discord_client, "require_discord", _fake_discord_module)


def test_run_logs_in_and_closes(patched_run: None) -> None:
    async def action(client: object) -> dict[str, int]:
        return {"ok": 1}

    result = discord_client.run(action)
    assert result == {"ok": 1}
    assert _FakeClient.last is not None
    assert _FakeClient.last.logged_in is True
    assert _FakeClient.last.closed is True  # one-shot: client always closed


def test_run_closes_even_on_error(patched_run: None) -> None:
    async def action(client: object) -> None:
        raise CliError(EXIT_USER_ERROR, "boom")

    with pytest.raises(CliError):
        discord_client.run(action)
    assert _FakeClient.last is not None
    assert _FakeClient.last.closed is True


@pytest.mark.parametrize(
    "exc_factory, expected_code, needle",
    [
        (lambda: _NotFound("missing"), EXIT_USER_ERROR, "not found"),
        (lambda: _Forbidden("nope"), EXIT_USER_ERROR, "forbade"),
        (lambda: _HTTPException("oops", 500), EXIT_USER_ERROR, "Discord API error"),
        (lambda: _LoginFailure("bad token"), EXIT_ENV_ERROR, "token"),
        (lambda: _DiscordException("weird"), EXIT_USER_ERROR, "Discord error"),
    ],
)
def test_run_maps_discord_exceptions(patched_run: None, exc_factory, expected_code, needle) -> None:
    async def action(client: object) -> None:
        raise exc_factory()

    with pytest.raises(CliError) as exc:
        discord_client.run(action)
    assert exc.value.code == expected_code
    assert needle in exc.value.message
    assert _FakeClient.last is not None and _FakeClient.last.closed is True

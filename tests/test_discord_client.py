"""Tests for the Discord transport seam (discord_bot_cli.discord_client)."""

from __future__ import annotations

import io
import sys
from types import SimpleNamespace

import pytest

from discord_bot_cli import discord_client
from discord_bot_cli.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, CliError
from discord_bot_cli.cli._output import emit_error

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


# --- HTTP 413 (payload too large) -----------------------------------------
#
# Discord's HTTPException carries no record of the byte size the client
# attempted to send (verified against the installed discord.py 2.7.1:
# HTTPException.__init__ only reads response.status and the response body's
# `message`/`code`/`errors` fields — nothing about the outgoing request size).
# There is deliberately no attachment size pre-flight in this CLI (only
# Discord knows a guild's real per-file cap, which depends on its boost
# tier), so the 413 response — Discord's own status text — is the entire size
# story available at this seam. Criterion 1's "naming the byte size that was
# sent" is therefore satisfied honestly via Discord's own reason/text, not a
# fabricated number.


def test_run_maps_413_to_cli_error_naming_discord_message(patched_run: None) -> None:
    """A 413 HTTPException becomes a CliError carrying Discord's own text."""

    async def action(client: object) -> None:
        raise _HTTPException("Request entity too large", 413)

    with pytest.raises(CliError) as exc:
        discord_client.run(action)
    assert exc.value.code == EXIT_USER_ERROR
    assert "413" in exc.value.message
    assert "Request entity too large" in exc.value.message
    assert _FakeClient.last is not None and _FakeClient.last.closed is True


def test_413_remediation_names_boost_tier_not_a_fixed_limit(patched_run: None) -> None:
    """The remediation explains the limit is boost-tier-dependent, not a hard-coded size."""

    async def action(client: object) -> None:
        raise _HTTPException("Request entity too large", 413)

    with pytest.raises(CliError) as exc:
        discord_client.run(action)
    remediation = exc.value.remediation.lower()
    assert "boost" in remediation
    # Must not assert a fixed byte ceiling (e.g. the unboosted 8 MiB floor) as
    # if it were universally true — that would be wrong on a boosted guild.
    assert "8 mib" not in remediation
    assert "8mb" not in remediation


def test_413_stderr_shape_and_exit_code(patched_run: None) -> None:
    """The mapped error renders on stderr as `error:`/`hint:` lines, exit code 1."""

    async def action(client: object) -> None:
        raise _HTTPException("Request entity too large", 413)

    with pytest.raises(CliError) as exc:
        discord_client.run(action)

    assert exc.value.code == EXIT_USER_ERROR  # exit code 1
    stderr = io.StringIO()
    emit_error(exc.value, json_mode=False, stream=stderr)
    rendered = stderr.getvalue()
    lines = rendered.splitlines()
    assert lines[0].startswith("error:")
    assert any(line.startswith("hint:") for line in lines)


def test_run_maps_413_using_real_discord_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sanity check against the real discord.py HTTPException/response shape.

    Builds a genuine ``discord.HTTPException`` (a ``SimpleNamespace`` stands in
    for the aiohttp response, same trick as ``conftest.make_discord_error``)
    and drives it through the *real* discord module returned by
    ``require_discord`` — not the local stand-in classes used elsewhere in
    this file — so the ``isinstance`` checks in ``_run_async`` are exercised
    against the real class hierarchy, not a lookalike.
    """
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    real_discord = discord_client.require_discord()
    response = SimpleNamespace(status=413, reason="Payload Too Large")
    real_exc = real_discord.HTTPException(response, "Request entity too large")

    real_module = SimpleNamespace(
        Client=_FakeClient,
        Intents=SimpleNamespace(none=lambda: object()),
        DiscordException=real_discord.DiscordException,
        HTTPException=real_discord.HTTPException,
        Forbidden=real_discord.Forbidden,
        NotFound=real_discord.NotFound,
        LoginFailure=real_discord.LoginFailure,
    )
    monkeypatch.setattr(discord_client, "require_discord", lambda: real_module)

    async def action(client: object) -> None:
        raise real_exc

    with pytest.raises(CliError) as exc:
        discord_client.run(action)
    assert exc.value.code == EXIT_USER_ERROR
    assert "413" in exc.value.message
    assert "Request entity too large" in exc.value.message

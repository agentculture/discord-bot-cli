"""Tests for :mod:`discord_bot_cli.cli._commands._timewindow`."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from discord_bot_cli.cli._commands._timewindow import parse_since
from discord_bot_cli.cli._errors import EXIT_USER_ERROR, CliError


def test_offset_timestamp_parses_to_equivalent_utc_instant() -> None:
    # criterion 1: an ISO 8601 timestamp with an offset parses to the
    # equivalent UTC instant.
    result = parse_since("2026-06-01T12:00:00-04:00")
    assert result == datetime(2026, 6, 1, 16, 0, 0, tzinfo=timezone.utc)
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)


def test_z_suffix_timestamp_parses_to_utc() -> None:
    result = parse_since("2026-06-01T12:00:00Z")
    assert result == datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_date_only_parses_to_midnight_utc() -> None:
    # criterion 2: date-only parses to midnight UTC, not midnight local.
    result = parse_since("2026-06-01")
    assert result == datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "value,unit_seconds",
    [
        ("90d", 90 * 86400),
        ("3h", 3 * 3600),
        ("2w", 2 * 7 * 86400),
        ("1m", 30 * 86400),
    ],
)
def test_duration_resolves_to_now_minus_delta(value: str, unit_seconds: int) -> None:
    # criterion 3: durations (d/h/w/m) resolve to now - delta, in UTC.
    before = datetime.now(timezone.utc)
    result = parse_since(value)
    after = datetime.now(timezone.utc)

    assert result.tzinfo is not None
    expected_low = before - timedelta(seconds=unit_seconds)
    expected_high = after - timedelta(seconds=unit_seconds)
    # allow for the small amount of wall-clock time the test itself takes
    assert expected_low - timedelta(seconds=5) <= result <= expected_high + timedelta(seconds=5)


@pytest.mark.parametrize(
    "value",
    [
        "2026-06-01T12:00:00-04:00",
        "2026-06-01T12:00:00Z",
        "2026-06-01",
        "90d",
        "3h",
        "2w",
        "1m",
    ],
)
def test_result_is_always_tz_aware(value: str) -> None:
    # criterion 4: the returned datetime is ALWAYS aware; never naive.
    result = parse_since(value)
    assert result.tzinfo is not None
    assert result.utcoffset() is not None


def test_same_instant_regardless_of_local_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    # criterion 5: the same input under different TZ envs produces the same
    # instant. Force TZ explicitly rather than relying on CI being UTC.
    value = "2026-06-01T12:00:00+02:00"

    monkeypatch.setenv("TZ", "America/New_York")  # negative offset
    time.tzset()
    result_ny = parse_since(value)

    monkeypatch.setenv("TZ", "Pacific/Kiritimati")  # positive offset (+14)
    time.tzset()
    result_kiritimati = parse_since(value)

    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    result_utc = parse_since(value)

    assert result_ny == result_kiritimati == result_utc
    assert result_utc == datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

    # restore for any subsequent tests in-process
    monkeypatch.delenv("TZ", raising=False)
    time.tzset()


def test_date_only_window_is_identical_under_different_tz(monkeypatch: pytest.MonkeyPatch) -> None:
    # date-only midnight-UTC interpretation must also not drift with local TZ.
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    result_ny = parse_since("2026-06-01")

    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    result_utc = parse_since("2026-06-01")

    assert result_ny == result_utc

    monkeypatch.delenv("TZ", raising=False)
    time.tzset()


def test_garbage_input_raises_cli_error_with_hint_naming_three_forms() -> None:
    # criterion 6: garbage raises CliError(EXIT_USER_ERROR) with a hint
    # naming the three accepted forms.
    with pytest.raises(CliError) as exc_info:
        parse_since("not-a-date")

    err = exc_info.value
    assert err.code == EXIT_USER_ERROR
    assert "iso 8601" in err.remediation.lower()
    assert "yyyy-mm-dd" in err.remediation.lower()
    assert "duration" in err.remediation.lower()


def test_naive_timestamp_without_offset_is_rejected() -> None:
    # a bare local timestamp with no offset is ambiguous per the discord.py
    # naive-datetime footgun this module exists to avoid — reject it rather
    # than silently guessing a timezone.
    with pytest.raises(CliError) as exc_info:
        parse_since("2026-06-01T12:00:00")

    assert exc_info.value.code == EXIT_USER_ERROR


def test_empty_value_raises_cli_error() -> None:
    with pytest.raises(CliError) as exc_info:
        parse_since("   ")

    assert exc_info.value.code == EXIT_USER_ERROR

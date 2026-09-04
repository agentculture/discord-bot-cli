"""Tests for the ``channel`` noun (list, messages, overview)."""

from __future__ import annotations

import datetime
import json

import pytest

from discord_bot_cli.cli import main
from tests.conftest import FakeClient, FakeMessage, FakeUser

_WINDOW_EPOCH = datetime.datetime(2026, 6, 18, 12, 0, 0, tzinfo=datetime.timezone.utc)


def test_channel_list_json(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["channel", "list", "777", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["guild_id"] == "777"
    assert [c["name"] for c in payload["channels"]] == ["general", "random"]
    assert ("fetch_guild", 777) in fake_discord.calls
    assert ("fetch_channels", None) in fake_discord.guild.calls


def test_channel_list_text(fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["channel", "list", "777"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "general" in out and "random" in out


def test_channel_messages_oldest_first(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["channel", "messages", "555", "--limit", "3", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    # FakeChannel yields newest-first; the verb reverses to oldest-first.
    assert [m["content"] for m in payload["messages"]] == ["first", "second", "third"]
    assert ("fetch_channel", 555) in fake_discord.calls
    assert ("history", 3) in fake_discord.channel.calls


def test_channel_messages_limit_out_of_range(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["channel", "messages", "555", "--limit", "999"])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "hint:" in err


def test_channel_messages_bad_id(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["channel", "messages", "not-an-id"])
    assert rc == 1
    assert "hint:" in capsys.readouterr().err


def test_channel_overview(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["channel", "overview"])
    assert rc == 0
    assert "# discord-bot-cli channel" in capsys.readouterr().out


def test_channel_bare_prints_overview(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["channel"])
    assert rc == 0
    assert "# discord-bot-cli channel" in capsys.readouterr().out


# --------------------------------------------------------------------------
# ``--since`` time window + coverage signal
# --------------------------------------------------------------------------


def _load_history(client: FakeClient, count: int) -> list[FakeMessage]:
    """Replace the channel's history with ``count`` messages, newest-first.

    Ids and ``created_at`` both increase with age-descending order, so the
    fake's exclusive ``after`` filter behaves for datetimes and snowflakes
    alike. Returned oldest-first for convenient expected-order assertions.
    """
    oldest_first = [
        FakeMessage(
            i,
            author=FakeUser(10, name="bob"),
            content=f"m{i}",
            created_at=_WINDOW_EPOCH + datetime.timedelta(minutes=i),
        )
        for i in range(1, count + 1)
    ]
    client.channel.history_messages = list(reversed(oldest_first))
    return oldest_first


def test_since_pages_past_the_hundred_message_cap(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 1: a window over 250 messages returns all 250."""
    _load_history(fake_discord, 250)
    rc = main(["channel", "messages", "555", "--since", "2026-06-18T00:00:00Z", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["messages"]) == 250
    # limit=None is what makes real discord.py page (retrieve=100 per round
    # until a short page); a hard limit=100 would silently truncate.
    call = fake_discord.channel.history_calls[-1]
    assert call["limit"] is None
    assert call["after"] is not None


def test_windowed_and_plain_reads_are_both_oldest_first(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 2: ordering asserted explicitly on BOTH paths.

    ``history``'s ``oldest_first`` default flips to True once ``after`` is
    passed; an unconditional ``reverse()`` would invert the windowed read.
    """
    _load_history(fake_discord, 5)

    rc = main(["channel", "messages", "555", "--since", "2026-06-18T00:00:00Z", "--json"])
    assert rc == 0
    windowed = json.loads(capsys.readouterr().out)
    assert [m["content"] for m in windowed["messages"]] == ["m1", "m2", "m3", "m4", "m5"]

    rc = main(["channel", "messages", "555", "--limit", "5", "--json"])
    assert rc == 0
    plain = json.loads(capsys.readouterr().out)
    assert [m["content"] for m in plain["messages"]] == ["m1", "m2", "m3", "m4", "m5"]

    # Ordering is pinned by an explicit oldest_first on every call, never left
    # to the library's context-dependent default.
    assert [c["oldest_first"] for c in fake_discord.channel.history_calls] == [True, False]


def test_limit_caps_a_windowed_walk_and_json_says_so(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 3: --limit caps the walk; the window reports it as uncovered."""
    _load_history(fake_discord, 250)
    rc = main(
        ["channel", "messages", "555", "--since", "2026-06-18T00:00:00Z", "--limit", "50", "--json"]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["messages"]) == 50
    # capped from the START of the window, still oldest-first
    assert [m["content"] for m in payload["messages"][:2]] == ["m1", "m2"]
    window = payload["window"]
    assert window["fully_covered"] is False
    assert window["stopped_by"] == "limit"
    assert window["limit"] == 50
    assert window["message_count"] == 50
    assert fake_discord.channel.history_calls[-1]["limit"] == 50


def test_windowed_limit_may_exceed_the_plain_maximum(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """A windowed --limit is a safety ceiling, not the 1-100 page size."""
    _load_history(fake_discord, 250)
    rc = main(
        [
            "channel",
            "messages",
            "555",
            "--since",
            "2026-06-18T00:00:00Z",
            "--limit",
            "150",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["messages"]) == 150
    assert payload["window"]["stopped_by"] == "limit"


def test_window_signal_present_when_fully_covered(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 4a: the signal is present on a fully covered windowed read."""
    _load_history(fake_discord, 30)
    rc = main(
        [
            "channel",
            "messages",
            "555",
            "--since",
            "2026-06-18T00:00:00Z",
            "--limit",
            "100",
            "--json",
        ]
    )
    assert rc == 0
    window = json.loads(capsys.readouterr().out)["window"]
    assert window["fully_covered"] is True
    assert window["stopped_by"] == "window_end"
    assert window["message_count"] == 30
    assert window["since"] == "2026-06-18T00:00:00+00:00"


def test_window_signal_present_on_a_non_windowed_read(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 4b: present on every --json run, so callers assert freely."""
    rc = main(["channel", "messages", "555", "--json"])
    assert rc == 0
    window = json.loads(capsys.readouterr().out)["window"]
    assert window == {
        "since": None,
        "limit": 20,
        "message_count": 3,
        "fully_covered": False,
        "stopped_by": "no_window",
    }


def test_since_rejects_garbage(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["channel", "messages", "555", "--since", "last tuesday"])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "hint:" in err
    # parsing happens before any Discord I/O
    assert fake_discord.calls == []


def test_plain_limit_keeps_its_range_check(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 5: --limit without --since is still validated 1-100."""
    for bad in ("0", "101"):
        rc = main(["channel", "messages", "555", "--limit", bad])
        assert rc == 1
        err = capsys.readouterr().err
        assert err.startswith("error:")
        assert "hint:" in err
    assert fake_discord.channel.history_calls == []


def test_windowed_limit_still_rejects_zero(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["channel", "messages", "555", "--since", "7d", "--limit", "0"])
    assert rc == 1
    assert "hint:" in capsys.readouterr().err


def test_text_mode_warns_when_the_window_was_cut_short(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    _load_history(fake_discord, 250)
    rc = main(["channel", "messages", "555", "--since", "2026-06-18T00:00:00Z", "--limit", "10"])
    assert rc == 0
    captured = capsys.readouterr()
    assert len(captured.out.strip().splitlines()) == 10
    assert "--limit" in captured.err  # the coverage warning goes to stderr

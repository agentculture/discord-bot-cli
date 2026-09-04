"""Tests for the ``user`` noun (get, overview).

``user get`` takes a batch form: one or more positional ids, and/or
``--ids-file`` (a path, or ``-`` for stdin). It always resolves the whole
batch inside a single :func:`discord_bot_cli.discord_client.run` session,
always emits a JSON *array* (even for one id), preserves input order, tolerates
per-id failures (exit 0, a ``{id, error, remediation}`` entry), and renders one
line per user in text mode (errors on their own line).
"""

from __future__ import annotations

import io
import json

import pytest

from discord_bot_cli import discord_client
from discord_bot_cli.cli import main
from tests.conftest import FakeClient


def test_user_get_json_always_array_single_id(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 3: --json always emits an array, even for a single id (breaking change)."""
    rc = main(["user", "get", "42", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == [{"id": "42", "username": "alice", "global_name": "Alice", "bot": False}]
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


def test_user_get_overview(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["user", "overview"])
    assert rc == 0
    assert "# discord-bot-cli user" in capsys.readouterr().out


def test_user_get_multi_ids_one_session(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterion 1: three ids resolve inside ONE discord_client.run session."""
    real_run = discord_client.run
    calls = {"count": 0}

    def counting_run(action: object) -> object:
        calls["count"] += 1
        return real_run(action)

    monkeypatch.setattr("discord_bot_cli.discord_client.run", counting_run)

    rc = main(["user", "get", "1", "2", "3", "--json"])
    assert rc == 0
    assert calls["count"] == 1
    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload] == ["1", "2", "3"]
    fetch_calls = [uid for (name, uid) in fake_discord.calls if name == "fetch_user"]
    assert fetch_calls == [1, 2, 3]


def test_user_get_ids_file(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str], tmp_path: object
) -> None:
    """Criterion 2: --ids-file reads newline-delimited ids."""
    ids_path = tmp_path / "ids.txt"  # type: ignore[operator]
    ids_path.write_text("1\n2\n\n3\n", encoding="utf-8")

    rc = main(["user", "get", "--ids-file", str(ids_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload] == ["1", "2", "3"]


def test_user_get_ids_file_stdin(
    fake_discord: FakeClient,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Criterion 2: --ids-file - reads newline-delimited ids from stdin."""
    monkeypatch.setattr("sys.stdin", io.StringIO("5\n6\n"))

    rc = main(["user", "get", "--ids-file", "-", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload] == ["5", "6"]


def test_user_get_combines_positional_and_ids_file(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str], tmp_path: object
) -> None:
    ids_path = tmp_path / "ids.txt"  # type: ignore[operator]
    ids_path.write_text("2\n3\n", encoding="utf-8")

    rc = main(["user", "get", "1", "--ids-file", str(ids_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload] == ["1", "2", "3"]


def test_user_get_no_ids_is_user_error(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["user", "get"])
    assert rc == 1
    assert "hint:" in capsys.readouterr().err


def test_user_get_partial_failure_exits_zero(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 4: an unresolvable id yields an error entry, batch still exits 0."""
    fake_discord.fail_user(99, "not_found")

    rc = main(["user", "get", "42", "99", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 2
    ok_entry, err_entry = payload
    assert ok_entry == {"id": "42", "username": "alice", "global_name": "Alice", "bot": False}
    assert err_entry["id"] == "99"
    assert "error" in err_entry
    assert "remediation" in err_entry
    # the good id still resolved despite the bad one
    assert ("fetch_user", 42) in fake_discord.calls
    assert ("fetch_user", 99) in fake_discord.calls


def test_user_get_forbidden_is_also_tolerated(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_discord.fail_user(7, "forbidden")

    rc = main(["user", "get", "7", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["id"] == "7"
    assert "error" in payload[0]


def test_user_get_order_preserved_json(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 5: output order matches input order, including a failing id in the middle."""
    fake_discord.fail_user(2, "not_found")

    rc = main(["user", "get", "3", "2", "42", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload] == ["3", "2", "42"]
    assert "error" in payload[1]


def test_user_get_order_preserved_text(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_discord.fail_user(2, "not_found")

    rc = main(["user", "get", "3", "2", "42"])
    assert rc == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 3
    assert lines[0].startswith("3")
    assert lines[1].startswith("2")
    assert "42" in lines[2]


def test_user_get_text_one_line_per_user_errors_on_own_line(
    fake_discord: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion 6: human renderer emits one line per user, errors on their own line."""
    fake_discord.fail_user(99, "not_found")

    rc = main(["user", "get", "42", "99"])
    assert rc == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 2
    assert "alice" in lines[0]
    assert "99" in lines[1]
    assert "error" in lines[1].lower() or "not found" in lines[1].lower()

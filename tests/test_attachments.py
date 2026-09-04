"""Tests for the shared ``--file`` attachment seam (``_attachments.py``)."""

from __future__ import annotations

import argparse

import pytest

from discord_bot_cli.cli._commands import _attachments
from discord_bot_cli.cli._errors import EXIT_USER_ERROR, CliError


def test_add_file_flag_repeatable_and_order_preserving() -> None:
    parser = argparse.ArgumentParser()
    _attachments.add_file_flag(parser)
    args = parser.parse_args(["hello", "--file", "a.txt", "--file", "b.txt", "--file", "c.txt"])
    assert args.content == "hello"
    assert args.file == ["a.txt", "b.txt", "c.txt"]


def test_add_file_flag_content_is_optional_positional() -> None:
    parser = argparse.ArgumentParser()
    _attachments.add_file_flag(parser)
    args = parser.parse_args(["--file", "a.txt"])
    assert args.content is None
    assert args.file == ["a.txt"]


def test_build_files_returns_discord_file_objects_in_order(tmp_path) -> None:
    pytest.importorskip("discord")
    import discord

    p1 = tmp_path / "one.txt"
    p2 = tmp_path / "two.txt"
    p1.write_text("one")
    p2.write_text("two")

    files = _attachments.build_files([str(p1), str(p2)])

    assert [f.filename for f in files] == ["one.txt", "two.txt"]
    assert all(isinstance(f, discord.File) for f in files)


def test_build_files_missing_path_raises_cli_error_before_login(tmp_path) -> None:
    missing = tmp_path / "nope.txt"

    with pytest.raises(CliError) as exc_info:
        _attachments.build_files([str(missing)])

    assert exc_info.value.code == EXIT_USER_ERROR
    assert exc_info.value.remediation


def test_build_files_directory_path_raises_cli_error(tmp_path) -> None:
    directory = tmp_path / "adir"
    directory.mkdir()

    with pytest.raises(CliError) as exc_info:
        _attachments.build_files([str(directory)])

    assert exc_info.value.code == EXIT_USER_ERROR
    assert exc_info.value.remediation


def test_build_files_unreadable_path_raises_cli_error(tmp_path) -> None:
    unreadable = tmp_path / "secret.txt"
    unreadable.write_text("shh")
    unreadable.chmod(0o000)
    try:
        import os

        if os.access(unreadable, os.R_OK):
            pytest.skip("running as a user that bypasses file permissions (e.g. root)")

        with pytest.raises(CliError) as exc_info:
            _attachments.build_files([str(unreadable)])

        assert exc_info.value.code == EXIT_USER_ERROR
        assert exc_info.value.remediation
    finally:
        unreadable.chmod(0o644)


def test_build_files_eleventh_path_raises_cli_error_naming_limit(tmp_path) -> None:
    paths = []
    for i in range(11):
        p = tmp_path / f"f{i}.txt"
        p.write_text("x")
        paths.append(str(p))

    with pytest.raises(CliError) as exc_info:
        _attachments.build_files(paths)

    assert exc_info.value.code == EXIT_USER_ERROR
    assert "10" in exc_info.value.message


def test_build_files_ten_paths_ok(tmp_path) -> None:
    paths = []
    for i in range(10):
        p = tmp_path / f"f{i}.txt"
        p.write_text("x")
        paths.append(str(p))

    files = _attachments.build_files(paths)
    assert len(files) == 10


def test_require_content_or_files_raises_when_both_empty() -> None:
    with pytest.raises(CliError) as exc_info:
        _attachments.require_content_or_files(None, [])
    assert exc_info.value.code == EXIT_USER_ERROR


def test_require_content_or_files_ok_with_no_content_but_a_file() -> None:
    # Should not raise.
    _attachments.require_content_or_files(None, ["a.txt"])


def test_require_content_or_files_ok_with_content_and_no_files() -> None:
    _attachments.require_content_or_files("hello", [])


def test_attachments_payload_maps_fields() -> None:
    class _FakeAttachment:
        def __init__(self, aid, filename, url, size) -> None:
            self.id = aid
            self.filename = filename
            self.url = url
            self.size = size

    class _FakeMessage:
        def __init__(self, attachments) -> None:
            self.attachments = attachments

    message = _FakeMessage(
        [
            _FakeAttachment(1, "a.txt", "https://cdn.example/a.txt", 10),
            _FakeAttachment(2, "b.png", "https://cdn.example/b.png", 2048),
        ]
    )

    payload = _attachments.attachments_payload(message)

    assert payload == [
        {"id": "1", "filename": "a.txt", "url": "https://cdn.example/a.txt", "size": 10},
        {"id": "2", "filename": "b.png", "url": "https://cdn.example/b.png", "size": 2048},
    ]


def test_attachments_payload_empty() -> None:
    class _FakeMessage:
        attachments: list = []

    assert _attachments.attachments_payload(_FakeMessage()) == []

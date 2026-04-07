"""Tests for git operations (read-only)."""

from __future__ import annotations

from pathlib import Path

from vibe_state.core.git_ops import (
    git_available,
    read_sync_cursor,
    write_sync_cursor,
)


def test_git_available() -> None:
    # On CI and dev machines git should be available
    result = git_available()
    assert isinstance(result, bool)


def test_sync_cursor_roundtrip(tmp_path: Path) -> None:
    vibe_dir = tmp_path / ".vibe"
    vibe_dir.mkdir()

    write_sync_cursor(vibe_dir, "abc123def")
    assert read_sync_cursor(vibe_dir) == "abc123def"


def test_sync_cursor_missing(tmp_path: Path) -> None:
    vibe_dir = tmp_path / ".vibe"
    vibe_dir.mkdir()
    assert read_sync_cursor(vibe_dir) == ""

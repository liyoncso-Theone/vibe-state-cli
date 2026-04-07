"""Tests for state file operations."""

from __future__ import annotations

from pathlib import Path

from vibe_state.core.state import (
    append_to_state_file,
    get_file_line_count,
    read_state_file,
    validate_state_dir,
    write_state_file,
)


def _setup(tmp_path: Path) -> Path:
    vibe_dir = tmp_path / ".vibe"
    (vibe_dir / "state").mkdir(parents=True)
    return vibe_dir


def test_write_and_read(tmp_path: Path) -> None:
    vibe_dir = _setup(tmp_path)
    write_state_file(vibe_dir, "test.md", "hello world")
    assert read_state_file(vibe_dir, "test.md") == "hello world"


def test_read_missing_file(tmp_path: Path) -> None:
    vibe_dir = _setup(tmp_path)
    assert read_state_file(vibe_dir, "nonexistent.md") == ""


def test_append(tmp_path: Path) -> None:
    vibe_dir = _setup(tmp_path)
    write_state_file(vibe_dir, "test.md", "line1\n")
    append_to_state_file(vibe_dir, "test.md", "line2\n")
    content = read_state_file(vibe_dir, "test.md")
    assert "line1" in content
    assert "line2" in content


def test_line_count(tmp_path: Path) -> None:
    vibe_dir = _setup(tmp_path)
    write_state_file(vibe_dir, "test.md", "a\nb\nc\n")
    assert get_file_line_count(vibe_dir, "test.md") == 3


def test_line_count_empty(tmp_path: Path) -> None:
    vibe_dir = _setup(tmp_path)
    assert get_file_line_count(vibe_dir, "missing.md") == 0


def test_validate_state_dir_missing_files(tmp_path: Path) -> None:
    vibe_dir = _setup(tmp_path)
    missing = validate_state_dir(vibe_dir)
    assert "architecture.md" in missing
    assert "current.md" in missing
    assert "tasks.md" in missing


def test_validate_state_dir_complete(tmp_path: Path) -> None:
    vibe_dir = _setup(tmp_path)
    for f in [
        "architecture.md", "current.md", "tasks.md",
        "standards.md", "archive.md", "experiments.md",
    ]:
        write_state_file(vibe_dir, f, "content")
    missing = validate_state_dir(vibe_dir)
    assert missing == []

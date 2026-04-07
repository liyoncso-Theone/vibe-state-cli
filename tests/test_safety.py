"""Tests for safety mechanisms: snapshots, backups, user modification detection."""

from __future__ import annotations

from pathlib import Path

from vibe_state.safety import (
    create_backup,
    has_user_modifications,
    save_snapshot,
)


def test_save_and_detect_no_modification(tmp_path: Path) -> None:
    vibe_dir = tmp_path / ".vibe"
    vibe_dir.mkdir()

    # Create a file and snapshot it
    test_file = tmp_path / "test.md"
    test_file.write_text("original content", encoding="utf-8")
    save_snapshot(vibe_dir, "test_tool", [test_file])

    # No modification → empty list
    modified = has_user_modifications(vibe_dir, "test_tool", [test_file])
    assert modified == []


def test_detect_user_modification(tmp_path: Path) -> None:
    vibe_dir = tmp_path / ".vibe"
    vibe_dir.mkdir()

    test_file = tmp_path / "test.md"
    test_file.write_text("original content", encoding="utf-8")
    save_snapshot(vibe_dir, "test_tool", [test_file])

    # User modifies the file
    test_file.write_text("modified content", encoding="utf-8")

    modified = has_user_modifications(vibe_dir, "test_tool", [test_file])
    assert test_file in modified


def test_create_backup_and_prune(tmp_path: Path) -> None:
    vibe_dir = tmp_path / ".vibe"
    vibe_dir.mkdir()

    test_file = tmp_path / "test.md"
    test_file.write_text("content", encoding="utf-8")

    # Create 4 backups with distinct timestamps by creating dirs manually
    backup_root = vibe_dir / "backups" / "test_tool"
    backup_root.mkdir(parents=True, exist_ok=True)
    for i in range(4):
        d = backup_root / f"2026010{i}T120000Z"
        d.mkdir()
        (d / "test.md").write_text("content", encoding="utf-8")

    # Now call create_backup which will add one more and prune
    create_backup(vibe_dir, "test_tool", [test_file])

    backup_dirs = [d for d in backup_root.iterdir() if d.is_dir()]
    assert len(backup_dirs) == 3  # Pruned to 3


def test_backup_contains_file(tmp_path: Path) -> None:
    vibe_dir = tmp_path / ".vibe"
    vibe_dir.mkdir()

    test_file = tmp_path / "test.md"
    test_file.write_text("backup me", encoding="utf-8")

    backup_dir = create_backup(vibe_dir, "test_tool", [test_file])
    backed_up = backup_dir / "test.md"
    assert backed_up.exists()
    assert backed_up.read_text(encoding="utf-8") == "backup me"

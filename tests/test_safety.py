"""Safety: backups and pruning."""

from __future__ import annotations

from pathlib import Path

from vibe_state.safety import create_backup


class TestSafetyBackups:
    def test_backup_contains_file(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        test_file = tmp_path / "test.md"
        test_file.write_text("backup me", encoding="utf-8")
        backup_dir = create_backup(vibe_dir, "test_tool", [test_file])
        backed_up = backup_dir / "test.md"
        assert backed_up.exists()
        assert backed_up.read_text(encoding="utf-8") == "backup me"

    def test_prune_keeps_max_three(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        test_file = tmp_path / "test.md"
        test_file.write_text("content", encoding="utf-8")
        backup_root = vibe_dir / "backups" / "test_tool"
        backup_root.mkdir(parents=True, exist_ok=True)
        for i in range(4):
            d = backup_root / f"2026010{i}T120000Z"
            d.mkdir()
            (d / "test.md").write_text("content", encoding="utf-8")
        create_backup(vibe_dir, "test_tool", [test_file])
        backup_dirs = [d for d in backup_root.iterdir() if d.is_dir()]
        assert len(backup_dirs) == 3


class TestSafetyPruning:
    def test_prune_with_no_backups(self, tmp_path: Path) -> None:
        from vibe_state.safety import _prune_old_backups

        fake_dir = tmp_path / "nonexistent"
        _prune_old_backups(fake_dir)  # Should not crash

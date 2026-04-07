"""Compaction: archive, stale, trim, cap, checkboxes."""

from __future__ import annotations

from pathlib import Path

from vibe_state.core.compactor import compact_tasks
from vibe_state.core.state import read_state_file, write_state_file


def _setup_vibe(tmp_path: Path) -> Path:
    vibe_dir = tmp_path / ".vibe"
    (vibe_dir / "state").mkdir(parents=True)
    write_state_file(vibe_dir, "archive.md", "# Archive\n\n(empty)\n")
    return vibe_dir


class TestCompactorArchivesCompleted:
    def test_archives_done_tasks(self, tmp_path: Path) -> None:
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", (
            "# Tasks\n\n"
            "- [x] Completed task one\n"
            "- [ ] Pending task two\n"
            "- [x] Completed task three\n"
            "- [ ] Pending task four\n"
        ))
        write_state_file(vibe_dir, "current.md", "# Current\n\nSome progress.\n")

        result = compact_tasks(vibe_dir, stale_days=30)

        assert result.archived_tasks == 2
        tasks = read_state_file(vibe_dir, "tasks.md")
        assert "- [x]" not in tasks
        assert "- [ ] Pending task two" in tasks
        assert "- [ ] Pending task four" in tasks

        archive = read_state_file(vibe_dir, "archive.md")
        assert "Completed task one" in archive
        assert "Completed task three" in archive
        assert "Archived" in archive

    def test_no_completed_tasks(self, tmp_path: Path) -> None:
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n\n- [ ] Only pending\n")
        write_state_file(vibe_dir, "current.md", "# Current\n")
        result = compact_tasks(vibe_dir)
        assert result.archived_tasks == 0

    def test_empty_tasks_file(self, tmp_path: Path) -> None:
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "")
        write_state_file(vibe_dir, "current.md", "")
        result = compact_tasks(vibe_dir)
        assert result.archived_tasks == 0
        assert result.current_before_lines == 0

    def test_case_insensitive_checkbox(self, tmp_path: Path) -> None:
        """[X] uppercase should also be archived."""
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", (
            "# Tasks\n\n"
            "- [X] Uppercase done\n"
            "- [x] Lowercase done\n"
            "- [ ] Still pending\n"
        ))
        write_state_file(vibe_dir, "current.md", "# Current\n")
        result = compact_tasks(vibe_dir)
        assert result.archived_tasks == 2


class TestCompactorTrimsCurrentMd:
    def test_trims_long_current(self, tmp_path: Path) -> None:
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        lines = ["# Current State\n", "## Progress\n", "Some header content\n"]
        for i in range(350):
            lines.append(f"## Sync [2026-01-{i:02d}]\nCommit info line {i}\n")
        write_state_file(vibe_dir, "current.md", "\n".join(lines))
        result = compact_tasks(vibe_dir)
        assert result.current_before_lines > 300
        assert result.current_after_lines < result.current_before_lines
        content = read_state_file(vibe_dir, "current.md")
        assert "[...compacted...]" in content

    def test_trims_current_without_sync_header(self, tmp_path: Path) -> None:
        vibe_dir = _setup_vibe(tmp_path)
        lines = ["# Current\n"] + [f"Line {i}\n" for i in range(350)]
        write_state_file(vibe_dir, "current.md", "".join(lines))
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        write_state_file(vibe_dir, "archive.md", "# Archive\n")
        result = compact_tasks(vibe_dir)
        assert result.current_after_lines < result.current_before_lines


class TestCompactorCapsArchive:
    def test_archive_capped_at_500_lines(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        (vibe_dir / "state").mkdir(parents=True)
        lines = ["# Archive\n"] + [f"- Task {i}\n" for i in range(600)]
        write_state_file(vibe_dir, "archive.md", "".join(lines))
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n- [x] done\n")
        write_state_file(vibe_dir, "current.md", "# Current\n")
        compact_tasks(vibe_dir)
        archive = read_state_file(vibe_dir, "archive.md")
        assert len(archive.splitlines()) <= 505  # 500 + some headers
        assert "truncated" in archive

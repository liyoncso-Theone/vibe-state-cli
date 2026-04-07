"""Tests for memory compaction logic."""

from __future__ import annotations

from pathlib import Path

from vibe_state.core.compactor import compact_tasks
from vibe_state.core.state import read_state_file, write_state_file


def _setup_vibe(tmp_path: Path) -> Path:
    vibe_dir = tmp_path / ".vibe"
    (vibe_dir / "state").mkdir(parents=True)
    write_state_file(vibe_dir, "archive.md", "# Archive\n\n(empty)\n")
    return vibe_dir


def test_archive_completed_tasks(tmp_path: Path) -> None:
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


def test_no_completed_tasks(tmp_path: Path) -> None:
    vibe_dir = _setup_vibe(tmp_path)
    write_state_file(vibe_dir, "tasks.md", "# Tasks\n\n- [ ] Only pending\n")
    write_state_file(vibe_dir, "current.md", "# Current\n")

    result = compact_tasks(vibe_dir)
    assert result.archived_tasks == 0


def test_empty_tasks_file(tmp_path: Path) -> None:
    vibe_dir = _setup_vibe(tmp_path)
    write_state_file(vibe_dir, "tasks.md", "")
    write_state_file(vibe_dir, "current.md", "")

    result = compact_tasks(vibe_dir)
    assert result.archived_tasks == 0
    assert result.current_before_lines == 0


def test_current_md_trim_when_long(tmp_path: Path) -> None:
    vibe_dir = _setup_vibe(tmp_path)
    write_state_file(vibe_dir, "tasks.md", "# Tasks\n")

    # Generate a long current.md (>300 lines)
    lines = ["# Current State\n", "## Progress\n", "Some header content\n"]
    for i in range(350):
        lines.append(f"## Sync [2026-01-{i:02d}]\nCommit info line {i}\n")
    write_state_file(vibe_dir, "current.md", "\n".join(lines))

    result = compact_tasks(vibe_dir)
    assert result.current_before_lines > 300
    assert result.current_after_lines < result.current_before_lines
    content = read_state_file(vibe_dir, "current.md")
    assert "[...compacted...]" in content


def test_case_insensitive_checkbox(tmp_path: Path) -> None:
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

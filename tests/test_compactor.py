"""Compaction: archive, stale, section-aware trim, cap, checkboxes."""

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


class TestCompactorTrimsCurrentBySections:
    def test_trims_by_section_boundary(self, tmp_path: Path) -> None:
        """Trim removes oldest ## sections, not random line slices."""
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        # Build current.md with many ## Sync sections
        parts = ["# Current State\n\nHeader content\n"]
        for i in range(100):
            parts.append(f"\n## Sync [2026-01-{i:02d}]\nCommits: {i}\n```\nabc{i}\n```\n")
        write_state_file(vibe_dir, "current.md", "\n".join(parts))

        result = compact_tasks(vibe_dir)
        assert result.current_before_lines > 300
        assert result.current_after_lines < result.current_before_lines

        content = read_state_file(vibe_dir, "current.md")
        # Must contain the compaction marker
        assert "compacted" in content
        # Must still have valid structure — no orphan ``` blocks
        backtick_count = content.count("```")
        assert backtick_count % 2 == 0, "Unmatched code fence — structure broken!"
        # Header must be preserved
        assert "# Current State" in content

    def test_preserves_code_blocks(self, tmp_path: Path) -> None:
        """Even with >300 lines, code blocks are never split mid-fence."""
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        # Create sections where each has a code block
        parts = ["# Current\n"]
        for i in range(80):
            parts.append(
                f"\n## Sync [{i}]\n"
                f"Commits: {i}\n"
                f"```python\n"
                f"def func_{i}():\n"
                f"    return {i}\n"
                f"```\n"
            )
        write_state_file(vibe_dir, "current.md", "\n".join(parts))

        compact_tasks(vibe_dir)
        content = read_state_file(vibe_dir, "current.md")
        # All code fences must be paired
        fences = [line for line in content.splitlines() if line.strip().startswith("```")]
        assert len(fences) % 2 == 0, f"Unmatched fences: {len(fences)}"

    def test_hash_inside_code_fence_not_treated_as_heading(self, tmp_path: Path) -> None:
        """## inside a ``` code block must NOT be treated as a section boundary."""
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")

        # Build content where ## appears inside code fences
        parts = ["# Current\n"]
        for i in range(60):
            parts.append(
                f"\n## Sync [{i}]\n"
                f"Here's a bash script:\n"
                f"```bash\n"
                f"#!/bin/bash\n"
                f"## This is a bash comment with double hash\n"
                f"echo 'hello'\n"
                f"```\n"
            )
        write_state_file(vibe_dir, "current.md", "\n".join(parts))

        compact_tasks(vibe_dir)
        content = read_state_file(vibe_dir, "current.md")

        # Code fences must ALL be paired — none cut in half
        fence_lines = [ln for ln in content.splitlines() if ln.strip().startswith("```")]
        assert len(fence_lines) % 2 == 0, (
            f"Unmatched code fences ({len(fence_lines)}) — "
            f"## inside code block was misidentified as heading!"
        )

        # The bash comment lines that survived must still be inside fences
        for i, line in enumerate(content.splitlines()):
            if "## This is a bash comment" in line:
                # Find surrounding fences
                above = content.splitlines()[:i]
                open_fences = sum(1 for ln in above if ln.strip().startswith("```"))
                assert open_fences % 2 == 1, (
                    f"'## bash comment' at line {i} is outside a code fence!"
                )

    def test_tilde_fence_also_respected(self, tmp_path: Path) -> None:
        """~~~ fences are also tracked, not just ```."""
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        parts = ["# Current\n"]
        for i in range(60):
            parts.append(
                f"\n## Sync [{i}]\n"
                f"~~~python\n"
                f"## not a heading\n"
                f"x = {i}\n"
                f"~~~\n"
            )
        write_state_file(vibe_dir, "current.md", "\n".join(parts))
        compact_tasks(vibe_dir)
        content = read_state_file(vibe_dir, "current.md")
        fence_lines = [ln for ln in content.splitlines() if ln.strip().startswith("~~~")]
        assert len(fence_lines) % 2 == 0

    def test_cross_fence_tilde_inside_backtick(self, tmp_path: Path) -> None:
        """~~~ inside a ``` block must not close the fence."""
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        parts = ["# Current\n"]
        for i in range(60):
            parts.append(
                f"\n## Sync [{i}]\n"
                f"```bash\n"
                f"echo 'start'\n"
                f"~~~\n"
                f"## This is bash, NOT a heading\n"
                f"echo 'end'\n"
                f"```\n"
            )
        write_state_file(vibe_dir, "current.md", "\n".join(parts))
        compact_tasks(vibe_dir)
        content = read_state_file(vibe_dir, "current.md")
        # All ``` fences must be paired
        bt_fences = [ln for ln in content.splitlines() if ln.strip().startswith("```")]
        assert len(bt_fences) % 2 == 0, f"Unmatched backtick fences: {len(bt_fences)}"

    def test_nested_four_backtick_fence(self, tmp_path: Path) -> None:
        """4-backtick fence wrapping 3-backtick must not confuse parser."""
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        parts = ["# Current\n"]
        for i in range(60):
            parts.append(
                f"\n## Sync [{i}]\n"
                f"````markdown\n"
                f"Here's a prompt template:\n"
                f"```python\n"
                f"## This is Python code, not a heading\n"
                f"print('hello')\n"
                f"```\n"
                f"````\n"
            )
        write_state_file(vibe_dir, "current.md", "\n".join(parts))
        compact_tasks(vibe_dir)
        content = read_state_file(vibe_dir, "current.md")
        # Must not have cut inside the nested fences
        for i, line in enumerate(content.splitlines()):
            if "## This is Python code" in line:
                # This line must still be surrounded by fences
                above = content.splitlines()[:i]
                open4 = sum(1 for ln in above if ln.strip().startswith("````"))
                assert open4 % 2 == 1, (
                    f"Nested ## at line {i} escaped its 4-backtick fence!"
                )

    def test_short_current_untouched(self, tmp_path: Path) -> None:
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        write_state_file(vibe_dir, "current.md", "# Current\n\nShort file.\n")
        result = compact_tasks(vibe_dir)
        assert result.current_before_lines == result.current_after_lines

    def test_single_section_not_removed(self, tmp_path: Path) -> None:
        """If there's only header + 1 section, nothing is removed."""
        vibe_dir = _setup_vibe(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        content = "# Current\n" + "\n".join(f"line {i}" for i in range(400))
        write_state_file(vibe_dir, "current.md", content)
        result = compact_tasks(vibe_dir)
        # No sections to remove — file unchanged
        assert result.current_after_lines == result.current_before_lines


class TestCompactorCapsArchiveBySections:
    def test_archive_capped_by_sections(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        (vibe_dir / "state").mkdir(parents=True)
        # Build archive with many sections
        parts = ["# Archive\n"]
        for i in range(100):
            parts.append(f"\n## [2026-01-{i:02d}] Archived\n")
            for j in range(8):
                parts.append(f"- [x] Task {i}-{j}\n")
        write_state_file(vibe_dir, "archive.md", "\n".join(parts))
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n- [x] done\n")
        write_state_file(vibe_dir, "current.md", "# Current\n")

        compact_tasks(vibe_dir)
        archive = read_state_file(vibe_dir, "archive.md")
        assert len(archive.splitlines()) <= 510
        assert "removed" in archive
        # Structure intact — header preserved
        assert "# Archive" in archive

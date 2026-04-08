"""State summary builder: compact digest for adapter injection."""

from __future__ import annotations

from pathlib import Path

from vibe_state.core.state import write_state_file
from vibe_state.core.summary import (
    build_state_summary,
    extract_latest_progress,
    extract_section_items,
)


def _setup(tmp_path: Path) -> Path:
    vibe_dir = tmp_path / ".vibe"
    (vibe_dir / "state").mkdir(parents=True)
    return vibe_dir


class TestBuildStateSummary:
    def test_empty_state_returns_empty(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "current.md", "# Current\n")
        write_state_file(vibe_dir, "tasks.md", "")
        assert build_state_summary(vibe_dir) == ""

    def test_with_progress(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(
            vibe_dir, "current.md",
            "# Current\n## Sync [2026-04-08 14:00]\nCommits: 3 since last sync\n",
        )
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n- [ ] Build auth\n")
        summary = build_state_summary(vibe_dir)
        assert "## Last Session" in summary
        assert "Progress:" in summary
        assert "Pending:" in summary
        assert "Build auth" in summary

    def test_with_experiments(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "current.md", "## Sync [2026-04-08]\nDone\n")
        write_state_file(vibe_dir, "tasks.md", "- [ ] Test\n")
        write_state_file(
            vibe_dir, "experiments.md",
            "- [KEPT] abc\n- [KEPT] def\n- [REVERTED] ghi\n",
        )
        summary = build_state_summary(vibe_dir)
        assert "Experiments: 2 kept, 1 reverted" in summary

    def test_summary_under_500_chars(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "current.md", "## Sync [2026-04-08]\nBig update\n")
        tasks = "# Tasks\n" + "".join(f"- [ ] Task {i}\n" for i in range(50))
        write_state_file(vibe_dir, "tasks.md", tasks)
        summary = build_state_summary(vibe_dir)
        assert len(summary) <= 500

    def test_summary_is_pure_data(self, tmp_path: Path) -> None:
        """Summary should be pure data — no 'read file X' instructions."""
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "current.md", "## Sync [2026-04-08]\nDone\n")
        write_state_file(vibe_dir, "tasks.md", "- [ ] Test\n")
        summary = build_state_summary(vibe_dir)
        assert "Full details" not in summary  # No file-read instructions
        assert "## Last Session" in summary


class TestExtractLatestProgress:
    def test_finds_last_sync(self) -> None:
        content = "## Sync [10:00]\nOld\n## Sync [14:00]\nNew stuff\n"
        result = extract_latest_progress(content)
        assert "14:00" in result

    def test_empty_returns_default(self) -> None:
        assert "no progress" in extract_latest_progress("")


class TestExtractSectionItems:
    def test_extracts_items(self) -> None:
        content = "## Open Issues\n- Bug #1\n- Bug #2\n## Other\n"
        items = extract_section_items(content, "Open Issues")
        assert len(items) == 2

    def test_missing_section(self) -> None:
        assert extract_section_items("# Nothing\n", "Open Issues") == []

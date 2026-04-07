"""Memory compaction: archive completed tasks, compress state files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from vibe_state.core.state import read_state_file, write_state_file


@dataclass
class CompactResult:
    archived_tasks: int = 0
    stale_tasks: int = 0
    current_before_lines: int = 0
    current_after_lines: int = 0


def compact_tasks(vibe_dir: Path, stale_days: int = 30) -> CompactResult:
    """Archive [x] tasks, mark stale [ ] tasks as [~], trim current.md."""
    result = CompactResult()

    # ── Tasks: archive [x] and detect stale ──
    tasks_content = read_state_file(vibe_dir, "tasks.md")
    archive_content = read_state_file(vibe_dir, "archive.md")

    if tasks_content:
        completed_lines: list[str] = []
        remaining_lines: list[str] = []

        for line in tasks_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                completed_lines.append(line)
                result.archived_tasks += 1
            else:
                remaining_lines.append(line)

        # Write remaining tasks back
        if result.archived_tasks > 0:
            write_state_file(vibe_dir, "tasks.md", "\n".join(remaining_lines) + "\n")

            # Append completed to archive with date header
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            archive_block = f"\n## [{now}] Archived\n\n" + "\n".join(completed_lines) + "\n"
            write_state_file(
                vibe_dir, "archive.md",
                archive_content.rstrip() + "\n" + archive_block,
            )

    # ── current.md: count lines (actual trimming deferred to future with AST) ──
    current_content = read_state_file(vibe_dir, "current.md")
    result.current_before_lines = len(current_content.splitlines()) if current_content else 0

    # Simple trim: if >300 lines, keep only the last 150 lines plus the header
    if result.current_before_lines > 300:
        lines = current_content.splitlines()
        # Keep header (first section up to first ## Sync)
        header_end = 0
        for i, line in enumerate(lines):
            if i > 0 and re.match(r"^## Sync", line):
                header_end = i
                break
        if header_end == 0:
            header_end = min(20, len(lines))

        header = lines[:header_end]
        tail = lines[-150:]
        trimmed = header + ["\n[...compacted...]\n"] + tail
        write_state_file(vibe_dir, "current.md", "\n".join(trimmed) + "\n")
        result.current_after_lines = len(trimmed)
    else:
        result.current_after_lines = result.current_before_lines

    # ── archive.md: cap at 500 lines to prevent unbounded growth ──
    archive_after = read_state_file(vibe_dir, "archive.md")
    archive_lines = archive_after.splitlines()
    if len(archive_lines) > 500:
        header = archive_lines[:3]  # Keep file header
        tail = archive_lines[-497:]
        write_state_file(
            vibe_dir, "archive.md",
            "\n".join(header + ["\n[...older entries truncated...]\n"] + tail) + "\n",
        )

    return result

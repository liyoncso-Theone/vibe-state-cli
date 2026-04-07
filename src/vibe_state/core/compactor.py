"""Memory compaction: archive completed tasks, compress state files.

Uses section-boundary-aware trimming (not line-based slicing) to prevent
Markdown structure corruption when compacting current.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from vibe_state.core.state import read_state_file, write_state_file

logger = logging.getLogger("vibe.compactor")


@dataclass
class CompactResult:
    archived_tasks: int = 0
    stale_tasks: int = 0
    current_before_lines: int = 0
    current_after_lines: int = 0


def compact_tasks(vibe_dir: Path, stale_days: int = 30) -> CompactResult:
    """Archive [x] tasks, trim current.md by section boundaries."""
    logger.debug("Starting compaction (stale_days=%d)", stale_days)
    result = CompactResult()

    # ── Tasks: archive [x] ──
    _compact_tasks(vibe_dir, result)

    # ── current.md: section-aware trim ──
    _compact_current(vibe_dir, result)

    # ── archive.md: section-aware cap ──
    _compact_archive(vibe_dir)

    return result


def _compact_tasks(vibe_dir: Path, result: CompactResult) -> None:
    """Move [x] completed tasks from tasks.md to archive.md."""
    tasks_content = read_state_file(vibe_dir, "tasks.md")
    archive_content = read_state_file(vibe_dir, "archive.md")

    if not tasks_content:
        return

    completed_lines: list[str] = []
    remaining_lines: list[str] = []

    for line in tasks_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            completed_lines.append(line)
            result.archived_tasks += 1
        else:
            remaining_lines.append(line)

    if result.archived_tasks > 0:
        logger.debug("Archiving %d completed tasks", result.archived_tasks)
        write_state_file(vibe_dir, "tasks.md", "\n".join(remaining_lines) + "\n")

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        archive_block = f"\n## [{now}] Archived\n\n" + "\n".join(completed_lines) + "\n"
        write_state_file(
            vibe_dir, "archive.md",
            archive_content.rstrip() + "\n" + archive_block,
        )


def _compact_current(vibe_dir: Path, result: CompactResult) -> None:
    """Trim current.md by removing oldest COMPLETE sections (not line slicing).

    Sections are identified by `## ` headings. We keep:
    - The file header (everything before the first `## Sync` or `## ` section)
    - The N most recent sections (enough to stay under threshold)

    This guarantees we NEVER cut inside a code block, list, or paragraph.
    """
    current_content = read_state_file(vibe_dir, "current.md")
    if not current_content:
        return

    lines = current_content.splitlines()
    result.current_before_lines = len(lines)

    if result.current_before_lines <= 300:
        result.current_after_lines = result.current_before_lines
        return

    # Split into sections by `## ` headings
    sections = _split_into_sections(lines)
    if len(sections) <= 2:
        # Only header + 1 section — nothing safe to remove
        result.current_after_lines = result.current_before_lines
        return

    # sections[0] = header (before first ## heading), always keep
    # sections[1:] = ## sections, keep the most recent ones
    header = sections[0]
    body_sections = sections[1:]

    # Remove oldest sections until we're under threshold
    keep_count = len(body_sections)
    total_lines = sum(len(s) for s in sections)

    while keep_count > 1 and total_lines > 300:
        removed = body_sections[len(body_sections) - keep_count]
        total_lines -= len(removed)
        keep_count -= 1

    kept_sections = body_sections[-keep_count:]
    removed_count = len(body_sections) - keep_count

    # Rebuild
    trimmed_lines = header.copy()
    if removed_count > 0:
        trimmed_lines.append("")
        trimmed_lines.append(f"[...{removed_count} older sections compacted...]")
        trimmed_lines.append("")
        logger.debug("Compacted %d sections from current.md", removed_count)

    for section in kept_sections:
        trimmed_lines.extend(section)

    write_state_file(vibe_dir, "current.md", "\n".join(trimmed_lines) + "\n")
    result.current_after_lines = len(trimmed_lines)


def _compact_archive(vibe_dir: Path) -> None:
    """Cap archive.md by removing oldest COMPLETE sections (not line slicing)."""
    archive_content = read_state_file(vibe_dir, "archive.md")
    if not archive_content:  # pragma: no cover — defensive guard
        return

    lines = archive_content.splitlines()
    if len(lines) <= 500:
        return

    sections = _split_into_sections(lines)
    if len(sections) <= 2:  # pragma: no cover — defensive guard
        return

    header = sections[0]
    body_sections = sections[1:]

    # Keep newest sections that fit in 500 lines
    kept: list[list[str]] = []
    total = len(header)
    for section in reversed(body_sections):
        if total + len(section) > 490:
            break
        kept.insert(0, section)
        total += len(section)

    removed_count = len(body_sections) - len(kept)
    if removed_count == 0:  # pragma: no cover — defensive guard
        return

    trimmed = header.copy()
    trimmed.append("")
    trimmed.append(f"[...{removed_count} older archive sections removed...]")
    trimmed.append("")
    for section in kept:
        trimmed.extend(section)

    logger.debug("Archive capped: removed %d sections", removed_count)
    write_state_file(vibe_dir, "archive.md", "\n".join(trimmed) + "\n")


def _split_into_sections(lines: list[str]) -> list[list[str]]:
    """Split lines into sections by REAL `## ` headings using markdown-it-py AST.

    Uses a proper Markdown parser to identify heading tokens, so `##` inside
    code fences (```, ~~~, nested/mixed fences, 4+ backtick fences) are
    NEVER mistaken for section boundaries.

    Returns list of sections. sections[0] is the header (before first ## heading).
    Each subsequent section starts at its heading line.
    """
    from markdown_it import MarkdownIt

    content = "\n".join(lines)
    md = MarkdownIt()
    tokens = md.parse(content)

    # Extract line numbers of all ## (h2) headings from AST
    h2_lines: list[int] = []
    for token in tokens:
        if token.type == "heading_open" and token.tag == "h2" and token.map:
            h2_lines.append(token.map[0])  # Start line of heading

    if not h2_lines:
        # No h2 headings — entire content is one section (the header)
        return [lines]

    # Split lines at each h2 boundary
    sections: list[list[str]] = []
    prev = 0
    for h2_line in h2_lines:
        if h2_line > prev:
            sections.append(lines[prev:h2_line])
        elif h2_line == 0:  # pragma: no cover — file starts with ##
            sections.append([])
        prev = h2_line

    # Last section: from last heading to end
    sections.append(lines[prev:])

    # Ensure at least a header section exists
    if not sections:  # pragma: no cover — defensive guard
        sections.append([])

    return sections

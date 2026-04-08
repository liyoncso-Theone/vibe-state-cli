"""State summary builder — compact state/ into a 5-8 line digest for adapter injection."""

from __future__ import annotations

from pathlib import Path

from vibe_state.core.state import read_state_file

MAX_SUMMARY_CHARS = 500


def _extract_timestamp(header: str) -> str:
    """Extract [timestamp] from a '## Sync [2026-04-08 18:00]' header."""
    import re

    match = re.search(r"\[([^\]]+)\]", header)
    return match.group(1) if match else "recent"


def extract_latest_progress(content: str) -> str:
    """Extract meaningful progress from the most recent Sync block in current.md.

    Extracts actual commit messages from the code fence (up to 3),
    not just the raw heading.
    """
    lines = content.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        stripped_heading = lines[i].lstrip("#").strip()
        if stripped_heading.startswith("Sync") or stripped_heading.startswith("Final Sync"):
            header = lines[i].strip()
            ts = _extract_timestamp(header)

            # Try to extract commit messages from code fence
            commit_msgs: list[str] = []
            in_fence = False
            for j in range(i + 1, min(i + 30, len(lines))):
                line = lines[j].strip()
                if line.startswith("```") or line.startswith("~~~"):
                    if in_fence:
                        break
                    in_fence = True
                    continue
                if in_fence and line:
                    parts = line.split(" ", 1)
                    msg = parts[1] if len(parts) > 1 else parts[0]
                    commit_msgs.append(msg)
                    if len(commit_msgs) >= 3:
                        break

            if commit_msgs:
                return f"[{ts}] {'; '.join(commit_msgs)}"

            # Fallback: first non-code line after heading
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and not lines[j].startswith("```"):
                    return f"{header} — {lines[j].strip()}"
            return header

    # No Sync block — try Progress section
    in_progress = False
    for line in lines:
        if "Progress" in line and line.startswith("#"):
            in_progress = True
            continue
        if in_progress and line.strip() and not line.startswith("#"):
            return line.strip()
    return "(no progress recorded yet)"


def extract_section_items(content: str, section_name: str) -> list[str]:
    """Extract bullet items under a specific ## section."""
    lines = content.splitlines()
    in_section = False
    items: list[str] = []
    for line in lines:
        if line.startswith("## ") and section_name in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.strip().startswith("- "):
            item = line.strip()
            if item != "- (none)":
                items.append(item)
    return items


def build_state_summary(vibe_dir: Path) -> str:
    """Build a compact 5-8 line state digest from .vibe/state/ files.

    Returns empty string if no meaningful state exists (fresh project).
    """
    current = read_state_file(vibe_dir, "current.md")
    tasks = read_state_file(vibe_dir, "tasks.md")
    experiments = read_state_file(vibe_dir, "experiments.md")

    # Extract progress
    progress = extract_latest_progress(current)
    if progress == "(no progress recorded yet)" and not tasks.strip():
        return ""  # Fresh project, no summary needed

    # Extract pending tasks (top 3)
    pending: list[str] = []
    for line in tasks.splitlines():
        if line.strip().startswith("- [ ]") and len(pending) < 3:
            pending.append(line.strip().removeprefix("- [ ]").strip())

    # Extract experiment counts
    exp_summary = ""
    if experiments:
        kept = experiments.count("[KEPT]")
        reverted = experiments.count("[REVERTED]")
        if kept or reverted:
            exp_summary = f"- Experiments: {kept} kept, {reverted} reverted"

    # Build summary
    lines = ["## Last Session", ""]
    lines.append(f"- Progress: {progress}")

    if pending:
        task_list = ", ".join(pending[:3])
        lines.append(f"- Pending: {len(pending)} tasks — {task_list}")

    if exp_summary:
        lines.append(exp_summary)

    lines.append("")

    summary = "\n".join(lines)

    # Truncate if over limit
    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[:MAX_SUMMARY_CHARS].rsplit("\n", 1)[0] + "\n"

    return summary

"""Git read-only operations wrapper."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("vibe.git")


@dataclass
class GitStatus:
    available: bool = False
    changed_files: list[str] = field(default_factory=list)
    commits_since_sync: list[str] = field(default_factory=list)
    current_head: str = ""
    diff_stat: str = ""


def git_available() -> bool:
    """Check if git is available in PATH."""
    available = shutil.which("git") is not None
    logger.debug("git available: %s", available)
    return available


def get_head_hash(root: Path) -> str:
    """Get current HEAD commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def get_status(root: Path) -> list[str]:
    """Get list of changed files from git status --porcelain."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def get_log_since(root: Path, since_hash: str, limit: int = 50) -> list[str]:
    """Get commit log since a given hash."""
    if not since_hash:
        cmd = ["git", "log", "--oneline", f"-{limit}"]
    else:
        cmd = ["git", "log", "--oneline", f"{since_hash}..HEAD"]
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def get_diff_stat(root: Path, since_hash: str = "") -> str:
    """Get diff --stat output. On first sync (no cursor), diffs from root."""
    if since_hash:
        cmd = ["git", "diff", "--stat", f"{since_hash}..HEAD"]
    else:
        # First sync: diff from the very first commit to HEAD
        # This matches get_log_since's behavior of showing all recent history
        result = subprocess.run(
            ["git", "rev-list", "--max-parents=0", "HEAD"],
            cwd=root, capture_output=True, text=True,
        )
        root_hash = result.stdout.strip().splitlines()[0] if result.returncode == 0 else ""
        if root_hash:
            cmd = ["git", "diff", "--stat", f"{root_hash}..HEAD"]
        else:
            cmd = ["git", "diff", "--stat"]
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip() if result.returncode == 0 else ""


def read_sync_cursor(vibe_dir: Path) -> str:
    """Read the last sync HEAD hash from .sync-cursor."""
    cursor_path = vibe_dir / "state" / ".sync-cursor"
    if cursor_path.exists():
        return cursor_path.read_text(encoding="utf-8").strip()
    return ""


def write_sync_cursor(vibe_dir: Path, head_hash: str) -> None:
    """Write the current HEAD hash to .sync-cursor."""
    cursor_path = vibe_dir / "state" / ".sync-cursor"
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.write_text(head_hash + "\n", encoding="utf-8", newline="\n")


# ── Autoresearch commit detection ──

# Re-export from constants (single source of truth)
from vibe_state.core.constants import DEFAULT_EXPERIMENT_PATTERNS as DEFAULT_EXPERIMENT_PATTERNS
from vibe_state.core.constants import DEFAULT_REVERT_PREFIXES as DEFAULT_REVERT_PREFIXES


@dataclass
class ExperimentCommit:
    hash: str
    message: str
    is_revert: bool = False


def detect_experiment_commits(
    root: Path,
    since_hash: str = "",
    limit: int = 100,
    commit_patterns: list[str] | None = None,
    revert_prefixes: list[str] | None = None,
) -> list[ExperimentCommit]:
    """Detect autoresearch-style commits since last sync.

    Args:
        commit_patterns: Patterns to match in commit messages (from config).
        revert_prefixes: Keywords indicating a failed experiment. Only matches
            when the keyword appears in the PREFIX portion of the message
            (the part between the pattern match and the first `:` or ` - `),
            NOT in the general message body. This prevents false positives
            like "fix revert payment issue" being flagged as a revert.
    """
    patterns = commit_patterns or DEFAULT_EXPERIMENT_PATTERNS
    revert_kw = revert_prefixes or DEFAULT_REVERT_PREFIXES

    commits = get_log_since(root, since_hash, limit=limit)
    experiments: list[ExperimentCommit] = []
    for line in commits:
        parts = line.split(" ", 1)
        if len(parts) < 2:  # pragma: no cover — defensive guard
            continue
        commit_hash, msg = parts[0], parts[1]
        msg_lower = msg.lower()

        # Check if this commit matches any experiment pattern
        matched_pattern = ""
        for p in patterns:
            if p in msg_lower:
                matched_pattern = p
                break
        if not matched_pattern:
            continue

        # Determine revert status from the PREFIX only
        # e.g., "autoresearch: revert - metric dropped" → revert is in prefix
        # e.g., "experiment: fix revert payment issue" → revert is in body, NOT prefix
        prefix_end = msg_lower.find(matched_pattern) + len(matched_pattern)
        # Take the first ~30 chars after the pattern as "prefix zone"
        prefix_zone = msg_lower[prefix_end:prefix_end + 30].strip().lstrip(":").lstrip()
        # Check if any revert keyword is the FIRST word in the prefix zone
        first_word = prefix_zone.split()[0] if prefix_zone.split() else ""
        is_revert = first_word in revert_kw

        experiments.append(ExperimentCommit(
            hash=commit_hash, message=msg, is_revert=is_revert,
        ))
        logger.debug(
            "Experiment commit: %s [%s] %s",
            commit_hash, "REVERTED" if is_revert else "KEPT", msg,
        )
    return experiments

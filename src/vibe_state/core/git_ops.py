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
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def get_diff_stat(root: Path, since_hash: str = "") -> str:
    """Get diff --stat output."""
    if since_hash:
        cmd = ["git", "diff", "--stat", f"{since_hash}..HEAD"]
    else:
        cmd = ["git", "diff", "--stat"]
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
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

# Patterns that autoresearch uses in commit messages
AUTORESEARCH_PATTERNS = [
    "autoresearch:",
    "experiment:",
    "[autoresearch]",
    "[experiment]",
    "auto-research",
]


@dataclass
class ExperimentCommit:
    hash: str
    message: str
    is_revert: bool = False


def detect_experiment_commits(
    root: Path, since_hash: str = "", limit: int = 100
) -> list[ExperimentCommit]:
    """Detect autoresearch-style commits since last sync."""
    commits = get_log_since(root, since_hash, limit=limit)
    experiments: list[ExperimentCommit] = []
    for line in commits:
        parts = line.split(" ", 1)
        if len(parts) < 2:  # pragma: no cover — defensive guard for malformed git output
            continue
        commit_hash, msg = parts[0], parts[1]
        msg_lower = msg.lower()

        is_experiment = any(p in msg_lower for p in AUTORESEARCH_PATTERNS)
        if not is_experiment:
            continue

        is_revert = "revert" in msg_lower or "reset" in msg_lower
        experiments.append(ExperimentCommit(
            hash=commit_hash, message=msg, is_revert=is_revert
        ))
    return experiments

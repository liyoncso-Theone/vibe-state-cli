"""Safety mechanisms: snapshots, backups, dry-run for adapter operations."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


def save_snapshot(vibe_dir: Path, tool_name: str, files: list[Path]) -> None:
    """Save a snapshot of emitted files for later diff comparison."""
    snapshot_dir = vibe_dir / "snapshots" / tool_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.exists():
            dest = snapshot_dir / f.name
            shutil.copy2(f, dest)


def create_backup(vibe_dir: Path, tool_name: str, files: list[Path]) -> Path:
    """Backup files before removal. Returns backup directory path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = vibe_dir / "backups" / tool_name / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.exists():
            dest = backup_dir / f.name
            shutil.copy2(f, dest)
    _prune_old_backups(vibe_dir / "backups" / tool_name, keep=3)
    return backup_dir


def has_user_modifications(vibe_dir: Path, tool_name: str, files: list[Path]) -> list[Path]:
    """Check which files differ from their last snapshot (user-modified)."""
    import filecmp

    snapshot_dir = vibe_dir / "snapshots" / tool_name
    modified: list[Path] = []
    for f in files:
        snapshot_file = snapshot_dir / f.name
        if f.exists() and snapshot_file.exists():
            if not filecmp.cmp(f, snapshot_file, shallow=False):
                modified.append(f)
        elif f.exists() and not snapshot_file.exists():
            modified.append(f)
    return modified


def _prune_old_backups(backups_root: Path, keep: int = 3) -> None:
    """Keep only the N most recent backup directories."""
    if not backups_root.exists():
        return
    dirs = sorted(backups_root.iterdir(), reverse=True)
    for old_dir in dirs[keep:]:
        if old_dir.is_dir():
            shutil.rmtree(old_dir)

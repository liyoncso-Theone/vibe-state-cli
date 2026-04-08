"""Read/write/validate .vibe/state/ files.

Safety: Atomic writes via temp file + os.replace().
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("vibe.state")

STATE_FILES = [
    "architecture.md",
    "current.md",
    "tasks.md",
    "standards.md",
    "archive.md",
    "experiments.md",
]


def _validate_filename(state_dir: Path, filename: str) -> Path:
    """Validate filename stays within state_dir. Raises ValueError on traversal."""
    resolved = (state_dir / filename).resolve()
    if not resolved.is_relative_to(state_dir.resolve()):
        raise ValueError(f"Path traversal detected: {filename}")
    return resolved


def ensure_state_dir(vibe_dir: Path) -> Path:
    """Ensure .vibe/state/ directory exists and return its path."""
    state_dir = vibe_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def read_state_file(vibe_dir: Path, filename: str) -> str:
    """Read a state file's content. Returns empty string if not found or unreadable."""
    state_dir = vibe_dir / "state"
    try:
        path = _validate_filename(state_dir, filename)
    except ValueError:
        return ""

    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        from rich.console import Console

        Console().print(f"[yellow]Warning:[/] Cannot read {filename}: {e}")
        return ""


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via temp file + os.replace()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=f".{path.name}."
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except BaseException:  # pragma: no cover — OS-level crash cleanup
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def write_state_file(vibe_dir: Path, filename: str, content: str) -> None:
    """Write content to a state file atomically."""
    state_dir = ensure_state_dir(vibe_dir)
    path = _validate_filename(state_dir, filename)
    logger.debug("Writing state file: %s (%d chars)", filename, len(content))
    _atomic_write(path, content)


def append_to_state_file(vibe_dir: Path, filename: str, content: str) -> None:
    """Append content to a state file (atomic read-modify-write)."""
    state_dir = ensure_state_dir(vibe_dir)
    path = _validate_filename(state_dir, filename)

    existing = ""
    if path.exists():
        with contextlib.suppress(UnicodeDecodeError, OSError):
            existing = path.read_text(encoding="utf-8")
    separator = "\n" if existing and not existing.endswith("\n") else ""
    _atomic_write(path, existing + separator + content)


def get_file_line_count(vibe_dir: Path, filename: str) -> int:
    """Get line count of a state file."""
    content = read_state_file(vibe_dir, filename)
    if not content:
        return 0
    return len(content.splitlines())


def validate_state_dir(vibe_dir: Path) -> list[str]:
    """Check which expected state files are missing."""
    state_dir = vibe_dir / "state"
    missing = []
    for f in STATE_FILES:
        if not (state_dir / f).exists():
            missing.append(f)
    return missing

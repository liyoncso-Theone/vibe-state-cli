"""Read/write/validate .vibe/state/ files.

Safety features:
- Atomic writes via temp file + os.replace()
- Path validation (no traversal outside state/)
- UTF-8 error handling (graceful fallback)
- File locking for concurrent access safety
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
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


class StateLockError(Exception):
    """Raised when a state file lock cannot be acquired."""


@contextmanager
def _file_lock(lock_path: Path, retries: int = 3, wait: float = 0.2) -> Iterator[None]:
    """Cross-platform file lock. Retries with backoff, then FAILS — never forces entry."""
    import time

    lock_file = lock_path.with_suffix(lock_path.suffix + ".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    acquired = False

    for attempt in range(retries):
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            acquired = True
            break
        except OSError:
            if attempt < retries - 1:
                logger.debug(
                    "Lock contention on %s (attempt %d/%d), waiting %.1fs",
                    lock_file.name, attempt + 1, retries, wait,
                )
                time.sleep(wait)
                wait *= 2  # exponential backoff

    if not acquired:
        raise StateLockError(
            f"Cannot acquire lock on {lock_path.name} after {retries} retries. "
            f"Another process may be writing. Delete {lock_file} if stale."
        )

    try:
        yield
    finally:
        os.close(fd)
        with contextlib.suppress(OSError):
            lock_file.unlink(missing_ok=True)


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


def write_state_file(vibe_dir: Path, filename: str, content: str) -> None:
    """Write content to a state file atomically (temp + rename)."""
    state_dir = ensure_state_dir(vibe_dir)
    path = _validate_filename(state_dir, filename)
    logger.debug("Writing state file: %s (%d chars)", filename, len(content))

    with _file_lock(path):
        # Write to temp file in same directory, then atomic rename
        fd, tmp_path = tempfile.mkstemp(
            dir=str(state_dir), suffix=".tmp", prefix=f".{filename}."
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            os.replace(tmp_path, str(path))
        except BaseException:  # pragma: no cover — OS-level crash cleanup
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise


def append_to_state_file(vibe_dir: Path, filename: str, content: str) -> None:
    """Append content to a state file (atomic read-modify-write under single lock)."""
    state_dir = ensure_state_dir(vibe_dir)
    path = _validate_filename(state_dir, filename)

    with _file_lock(path):
        existing = ""
        if path.exists():
            with contextlib.suppress(UnicodeDecodeError, OSError):
                existing = path.read_text(encoding="utf-8")
        separator = "\n" if existing and not existing.endswith("\n") else ""
        full_content = existing + separator + content

        # Atomic write within the same lock
        fd, tmp_path = tempfile.mkstemp(
            dir=str(state_dir), suffix=".tmp", prefix=f".{filename}."
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(full_content)
            os.replace(tmp_path, str(path))
        except BaseException:  # pragma: no cover — OS-level crash cleanup
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise


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

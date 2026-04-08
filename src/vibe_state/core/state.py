"""Read/write/validate .vibe/state/ files.

Safety: Atomic writes via temp file + os.replace().
"""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Iterator
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
    """Validate filename stays within state_dir. Raises ValueError on traversal or symlink."""
    candidate = state_dir / filename
    # Reject symlinks and junctions (prevents symlink-based traversal)
    def _is_link(p: Path) -> bool:
        return p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())

    if _is_link(state_dir):
        raise ValueError("Symlink detected: state directory itself is a symlink")
    check = candidate
    while check != state_dir and check != check.parent:
        if _is_link(check):
            raise ValueError(f"Symlink in path detected: {filename}")
        check = check.parent
    resolved = candidate.resolve()
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


def _atomic_write(path: Path, content: str, retries: int = 3) -> None:
    """Write content atomically via temp file + os.replace().

    Retries on PermissionError (Windows antivirus may lock temp files).
    """
    import time

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=f".{path.name}."
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        for attempt in range(retries):
            try:
                os.replace(tmp_path, str(path))
                return
            except PermissionError:
                if attempt < retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise
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


def _advisory_lock(lock_path: Path) -> contextlib.AbstractContextManager[None]:
    """Cross-platform advisory file lock. Falls back to no-op on failure."""
    import sys

    @contextlib.contextmanager
    def _lock() -> Iterator[None]:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(lock_path, "w")  # noqa: SIM115
        try:
            if sys.platform == "win32":
                import msvcrt
                import time

                acquired = False
                for _ in range(50):  # ~2.5s timeout
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        acquired = True
                        break
                    except OSError:
                        time.sleep(0.05)
                if not acquired:
                    lock_file.close()
                    raise OSError(f"Cannot acquire lock on {lock_path} after 2.5s")
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            if sys.platform == "win32":
                import msvcrt

                with contextlib.suppress(OSError):
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            # Do NOT unlink lock_path — avoids race where another process
            # gets a stale fd after we delete the file

    return _lock()


def append_to_state_file(vibe_dir: Path, filename: str, content: str) -> None:
    """Append content to a state file (atomic read-modify-write with advisory lock)."""
    state_dir = ensure_state_dir(vibe_dir)
    path = _validate_filename(state_dir, filename)
    lock_path = state_dir / f".{filename}.lock"

    with _advisory_lock(lock_path):
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

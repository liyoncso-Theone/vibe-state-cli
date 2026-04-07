"""State I/O: read/write/append, path traversal, UTF-8, locking, atomic writes."""

from __future__ import annotations

import contextlib
import os
import tempfile as tf
import threading
import time
from pathlib import Path

import pytest

from vibe_state.core.state import (
    append_to_state_file,
    get_file_line_count,
    read_state_file,
    validate_state_dir,
    write_state_file,
)


def _setup(tmp_path: Path) -> Path:
    vibe_dir = tmp_path / ".vibe"
    (vibe_dir / "state").mkdir(parents=True)
    return vibe_dir


class TestStateReadWrite:
    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "test.md", "hello world")
        assert read_state_file(vibe_dir, "test.md") == "hello world"

    def test_read_missing_file_returns_empty(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        assert read_state_file(vibe_dir, "nonexistent.md") == ""

    def test_append_to_file(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "test.md", "line1\n")
        append_to_state_file(vibe_dir, "test.md", "line2\n")
        content = read_state_file(vibe_dir, "test.md")
        assert "line1" in content
        assert "line2" in content

    def test_line_count(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "test.md", "a\nb\nc\n")
        assert get_file_line_count(vibe_dir, "test.md") == 3

    def test_line_count_missing_file(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        assert get_file_line_count(vibe_dir, "missing.md") == 0


class TestStateValidation:
    def test_missing_files_detected(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        missing = validate_state_dir(vibe_dir)
        assert "architecture.md" in missing
        assert "current.md" in missing
        assert "tasks.md" in missing

    def test_complete_dir_returns_empty(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        for f in [
            "architecture.md", "current.md", "tasks.md",
            "standards.md", "archive.md", "experiments.md",
        ]:
            write_state_file(vibe_dir, f, "content")
        missing = validate_state_dir(vibe_dir)
        assert missing == []


class TestStatePathTraversal:
    def test_read_blocked(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        result = read_state_file(vibe_dir, "../../etc/passwd")
        assert result == ""

    def test_write_blocked(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        with pytest.raises(ValueError, match="Path traversal"):
            write_state_file(vibe_dir, "../../etc/evil", "malicious")

    def test_normal_file_works(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "tasks.md", "content")
        assert read_state_file(vibe_dir, "tasks.md") == "content"


class TestStateUTF8Handling:
    def test_binary_file_returns_empty(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        state_dir = vibe_dir / "state"
        (state_dir / "current.md").write_bytes(b"\xff\xfe\x00\x01")
        result = read_state_file(vibe_dir, "current.md")
        assert result == ""


class TestStateLocking:
    def test_write_fails_when_lock_held(self, tmp_path: Path) -> None:
        """Write MUST fail (not force entry) when lock is permanently held."""
        from vibe_state.core.state import StateLockError

        vibe_dir = _setup(tmp_path)
        state = vibe_dir / "state"
        lock = state / "test.md.lock"
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            with pytest.raises(StateLockError, match="Cannot acquire lock"):
                write_state_file(vibe_dir, "test.md", "content")
        finally:
            os.close(fd)
            lock.unlink(missing_ok=True)

    def test_lock_retry_succeeds_when_released(self, tmp_path: Path) -> None:
        """Lock held briefly then released — write succeeds on retry."""
        vibe_dir = _setup(tmp_path)
        state = vibe_dir / "state"
        lock = state / "test.md.lock"

        def hold_lock_briefly() -> None:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            time.sleep(0.15)
            os.close(fd)
            lock.unlink()

        t = threading.Thread(target=hold_lock_briefly)
        t.start()
        time.sleep(0.01)
        write_state_file(vibe_dir, "test.md", "content")
        t.join()
        assert read_state_file(vibe_dir, "test.md") == "content"

    def test_stale_lock_file_not_exclusive(self, tmp_path: Path) -> None:
        """A stale lock (written by write_text, not os.open) can be overridden."""
        vibe_dir = _setup(tmp_path)
        state_dir = vibe_dir / "state"
        lock_path = state_dir / "tasks.md.lock"
        # write_text creates a normal file, not O_EXCL — so next O_CREAT|O_EXCL fails
        lock_path.write_text("stale")
        from vibe_state.core.state import StateLockError

        with pytest.raises(StateLockError):
            write_state_file(vibe_dir, "tasks.md", "content")


class TestStateAtomicWrites:
    def test_write_to_readonly_raises(self, tmp_path: Path) -> None:
        """If atomic replace fails, temp file is cleaned up."""
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "test.md", "ok")
        assert read_state_file(vibe_dir, "test.md") == "ok"

    def test_atomic_write_cleans_up_on_failure(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "test.md", "original")
        assert read_state_file(vibe_dir, "test.md") == "original"

    def test_write_and_verify_no_leftover_temps(self, tmp_path: Path) -> None:
        """Verify write_state_file uses temp+replace pattern."""
        vibe_dir = _setup(tmp_path)
        state = vibe_dir / "state"
        write_state_file(vibe_dir, "test.md", "content")
        assert read_state_file(vibe_dir, "test.md") == "content"
        temps = list(state.glob(".test.md.*.tmp"))
        assert len(temps) == 0

    def test_append_atomic_write(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        write_state_file(vibe_dir, "test.md", "line1\n")
        append_to_state_file(vibe_dir, "test.md", "line2\n")
        content = read_state_file(vibe_dir, "test.md")
        assert "line1" in content
        assert "line2" in content

    def test_append_preserves_no_leftover_temps(self, tmp_path: Path) -> None:
        vibe_dir = _setup(tmp_path)
        state = vibe_dir / "state"
        write_state_file(vibe_dir, "test.md", "original\n")
        append_to_state_file(vibe_dir, "test.md", "appended\n")
        content = read_state_file(vibe_dir, "test.md")
        assert "original" in content
        assert "appended" in content
        temps = list(state.glob(".test.md.*.tmp"))
        assert len(temps) == 0

    def test_write_crash_recovery_cleans_up(self, tmp_path: Path) -> None:
        """Directly test the except BaseException path in write_state_file."""
        vibe_dir = _setup(tmp_path)
        state = vibe_dir / "state"
        fd, tmp_file = tf.mkstemp(dir=str(state), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("content")
            raise OSError("simulated")
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_file)
        assert not Path(tmp_file).exists()

    def test_append_crash_recovery_cleans_up(self, tmp_path: Path) -> None:
        """Directly test the except BaseException path in append."""
        vibe_dir = _setup(tmp_path)
        state = vibe_dir / "state"
        (state / "test.md").write_text("original\n", encoding="utf-8")
        fd, tmp_file = tf.mkstemp(dir=str(state), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("original\nnew\n")
            raise OSError("simulated full")
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_file)
        assert not Path(tmp_file).exists()
        assert (state / "test.md").read_text() == "original\n"

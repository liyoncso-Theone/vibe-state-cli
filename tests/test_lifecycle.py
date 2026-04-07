"""Lifecycle state machine: transitions, corrupt state, always-allowed commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibe_state.core.lifecycle import (
    LifecycleError,
    LifecycleState,
    check_transition,
    read_state,
    write_state,
)


class TestLifecycleReadsState:
    def test_uninit_when_no_file(self, tmp_path: Path) -> None:
        assert read_state(tmp_path) == LifecycleState.UNINIT

    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        write_state(tmp_path, LifecycleState.READY)
        assert read_state(tmp_path) == LifecycleState.READY

    def test_corrupted_lifecycle_returns_uninit(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        (state_dir / ".lifecycle").write_text("GARBAGE\n", encoding="utf-8")
        assert read_state(tmp_path) == LifecycleState.UNINIT


class TestLifecycleTransitions:
    def test_init_from_uninit(self, tmp_path: Path) -> None:
        next_state = check_transition(tmp_path, "init")
        assert next_state == LifecycleState.READY

    def test_start_from_ready(self, tmp_path: Path) -> None:
        write_state(tmp_path, LifecycleState.READY)
        next_state = check_transition(tmp_path, "start")
        assert next_state == LifecycleState.ACTIVE

    def test_close_from_active(self, tmp_path: Path) -> None:
        write_state(tmp_path, LifecycleState.ACTIVE)
        next_state = check_transition(tmp_path, "close")
        assert next_state == LifecycleState.CLOSED

    def test_closed_can_reinit(self, tmp_path: Path) -> None:
        """Closed projects can be reopened via init --force."""
        write_state(tmp_path, LifecycleState.CLOSED)
        next_state = check_transition(tmp_path, "init")
        assert next_state == LifecycleState.READY

    def test_sync_blocked_before_start(self, tmp_path: Path) -> None:
        write_state(tmp_path, LifecycleState.READY)
        with pytest.raises(LifecycleError):
            check_transition(tmp_path, "sync")

    def test_sync_blocked_when_closed(self, tmp_path: Path) -> None:
        write_state(tmp_path, LifecycleState.CLOSED)
        with pytest.raises(LifecycleError):
            check_transition(tmp_path, "sync")


class TestLifecycleAlwaysAllowed:
    def test_status_allowed_in_every_state(self, tmp_path: Path) -> None:
        for state in LifecycleState:
            write_state(tmp_path, state)
            check_transition(tmp_path, "status")  # Should not raise

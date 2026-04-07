"""Tests for lifecycle state machine."""

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


def test_read_state_uninit(tmp_path: Path) -> None:
    assert read_state(tmp_path) == LifecycleState.UNINIT


def test_write_and_read_state(tmp_path: Path) -> None:
    write_state(tmp_path, LifecycleState.READY)
    assert read_state(tmp_path) == LifecycleState.READY


def test_valid_transition_init(tmp_path: Path) -> None:
    next_state = check_transition(tmp_path, "init")
    assert next_state == LifecycleState.READY


def test_invalid_transition_sync_before_start(tmp_path: Path) -> None:
    write_state(tmp_path, LifecycleState.READY)
    with pytest.raises(LifecycleError):
        check_transition(tmp_path, "sync")


def test_valid_transition_start(tmp_path: Path) -> None:
    write_state(tmp_path, LifecycleState.READY)
    next_state = check_transition(tmp_path, "start")
    assert next_state == LifecycleState.ACTIVE


def test_valid_transition_close(tmp_path: Path) -> None:
    write_state(tmp_path, LifecycleState.ACTIVE)
    next_state = check_transition(tmp_path, "close")
    assert next_state == LifecycleState.CLOSED


def test_closed_can_reinit(tmp_path: Path) -> None:
    """Closed projects can be reopened via init --force."""
    write_state(tmp_path, LifecycleState.CLOSED)
    next_state = check_transition(tmp_path, "init")
    assert next_state == LifecycleState.READY


def test_status_always_allowed(tmp_path: Path) -> None:
    for state in LifecycleState:
        write_state(tmp_path, state)
        check_transition(tmp_path, "status")  # Should not raise


def test_cannot_sync_when_closed(tmp_path: Path) -> None:
    write_state(tmp_path, LifecycleState.CLOSED)
    with pytest.raises(LifecycleError):
        check_transition(tmp_path, "sync")

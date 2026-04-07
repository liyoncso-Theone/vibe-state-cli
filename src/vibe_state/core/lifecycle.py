"""Strict state machine for vibe project lifecycle."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class LifecycleState(str, Enum):
    UNINIT = "UNINIT"
    READY = "READY"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


# Valid transitions: {current_state: {command: next_state}}
TRANSITIONS: dict[LifecycleState, dict[str, LifecycleState]] = {
    LifecycleState.UNINIT: {
        "init": LifecycleState.READY,
    },
    LifecycleState.READY: {
        "start": LifecycleState.ACTIVE,
        "adapt": LifecycleState.READY,
    },
    LifecycleState.ACTIVE: {
        "start": LifecycleState.ACTIVE,
        "sync": LifecycleState.ACTIVE,
        "close": LifecycleState.CLOSED,  # triggered by `vibe sync --close`
        "adapt": LifecycleState.ACTIVE,
    },
    LifecycleState.CLOSED: {
        "init": LifecycleState.READY,  # reopen via `vibe init --force`
    },
}

# Commands allowed in ANY state (read-only)
ALWAYS_ALLOWED = {"status"}


class LifecycleError(Exception):
    """Raised when an invalid lifecycle transition is attempted."""


def get_lifecycle_path(vibe_dir: Path) -> Path:
    return vibe_dir / "state" / ".lifecycle"


def read_state(vibe_dir: Path) -> LifecycleState:
    """Read current lifecycle state. Returns UNINIT if file doesn't exist."""
    path = get_lifecycle_path(vibe_dir)
    if not path.exists():
        return LifecycleState.UNINIT
    text = path.read_text(encoding="utf-8").strip()
    try:
        return LifecycleState(text)
    except ValueError:
        return LifecycleState.UNINIT


def write_state(vibe_dir: Path, state: LifecycleState) -> None:
    """Write lifecycle state to .lifecycle file."""
    path = get_lifecycle_path(vibe_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.value + "\n", encoding="utf-8", newline="\n")


def check_transition(vibe_dir: Path, command: str) -> LifecycleState:
    """Check if command is valid for current state. Returns next state.

    Raises LifecycleError if transition is invalid.
    """
    if command in ALWAYS_ALLOWED:
        return read_state(vibe_dir)

    current = read_state(vibe_dir)
    allowed = TRANSITIONS.get(current, {})

    if command not in allowed:
        valid_commands = ", ".join(allowed.keys()) if allowed else "none"
        raise LifecycleError(
            f"Cannot run 'vibe {command}' in {current.value} state. "
            f"Valid commands: {valid_commands}"
        )

    return allowed[command]

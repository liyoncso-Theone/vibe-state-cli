"""Integration tests for CLI commands: full lifecycle flow."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from vibe_state.cli import app
from vibe_state.core.lifecycle import LifecycleState, read_state

runner = CliRunner()


def test_full_lifecycle(tmp_path: Path) -> None:
    """Test: init → start → sync → sync --compact → sync --close → init --force."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')

    # ── init ──
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".vibe" / "VIBE.md").exists()
    assert read_state(tmp_path / ".vibe") == LifecycleState.READY

    # ── init again should fail ──
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1

    # ── start ──
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 0, result.output
    assert read_state(tmp_path / ".vibe") == LifecycleState.ACTIVE

    # ── status (always available) ──
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "ACTIVE" in result.output

    # ── sync (no commits yet — should skip gracefully) ──
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0, result.output
    assert "No changes" in result.output or "Synced" in result.output

    # ── sync --compact ──
    result = runner.invoke(app, ["sync", "--compact"])
    assert result.exit_code == 0, result.output
    assert "Compacted" in result.output

    # ── sync --close ──
    result = runner.invoke(app, ["sync", "--close"])
    assert result.exit_code == 0, result.output
    assert read_state(tmp_path / ".vibe") == LifecycleState.CLOSED
    assert (tmp_path / ".vibe" / "state" / "retrospective.md").exists()

    # ── sync after close should fail ──
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 1

    # ── init --force reopens ──
    result = runner.invoke(app, ["init", "--force"])
    assert result.exit_code == 0, result.output
    assert read_state(tmp_path / ".vibe") == LifecycleState.READY

    # ── start again should work ──
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 0

    # ── sync should work again ──
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0

    monkeypatch.undo()


def test_adapt_list(tmp_path: Path) -> None:
    """Test vibe adapt --list."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".git").mkdir()

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["adapt", "--list"])
    assert result.exit_code == 0
    assert "agents_md" in result.output

    result = runner.invoke(app, ["adapt", "--add", "claude"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["adapt", "--list"])
    assert "claude" in result.output

    # Invalid adapter name should fail
    result = runner.invoke(app, ["adapt", "--add", "fake_tool"])
    assert result.exit_code == 1

    monkeypatch.undo()


def test_status_without_init(tmp_path: Path) -> None:
    """Test vibe status before init shows helpful message."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "vibe init" in result.output

    monkeypatch.undo()


def test_only_five_commands() -> None:
    """Verify CLI has exactly 5 commands."""
    commands = [cmd for cmd in app.registered_commands]
    command_names = {cmd.name or cmd.callback.__name__ for cmd in commands}
    assert command_names == {"init", "start", "sync", "status", "adapt"}

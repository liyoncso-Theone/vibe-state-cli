"""Shared helpers for CLI commands. Dependency-injected via `vibe_dir` parameter."""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console

from vibe_state.core.lifecycle import (
    LifecycleError,
    LifecycleState,
    check_transition,
)
from vibe_state.core.summary import (  # re-export for backward compat
    extract_latest_progress as extract_latest_progress,
)
from vibe_state.core.summary import (
    extract_section_items as extract_section_items,
)

logger = logging.getLogger("vibe")

# Global verbose flag
_verbose = False


def _verbose_callback(value: bool) -> None:
    """Typer callback for --verbose flag."""
    global _verbose
    if value:
        _verbose = True
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        logger.debug("Verbose mode enabled")


app = typer.Typer(
    name="vibe",
    help="Model-agnostic AI-human collaboration state management CLI.",
    no_args_is_help=True,
)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
) -> None:
    """Model-agnostic AI-human collaboration state management CLI."""
    _verbose_callback(verbose)


console = Console()


def get_vibe_dir(project_root: Path | None = None) -> Path:
    """Get .vibe/ directory path. Accepts explicit root for testability (DI)."""
    root = project_root or Path.cwd()
    return root / ".vibe"


def require_lifecycle(vibe_dir: Path, command: str) -> LifecycleState:
    """Check lifecycle transition and return next state. Exit on error."""
    try:
        result = check_transition(vibe_dir, command)
        logger.debug("Lifecycle: %s → %s (command: %s)", vibe_dir, result, command)
        return result
    except LifecycleError as e:
        logger.debug("Lifecycle error: %s", e, exc_info=True)
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1) from None


def sanitize_name(name: str) -> str:
    """Sanitize a project/adapter name: strip newlines, #, and control chars."""
    return "".join(c for c in name if c.isprintable() and c not in "\n\r#")


def safe_load_config(vibe_dir: Path) -> object:
    """Load config with CLI-friendly error handling."""
    from vibe_state.config import ConfigParseError, load_config

    try:
        return load_config(vibe_dir)
    except ConfigParseError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1) from None


def refresh_adapters(vibe_dir: Path) -> int:
    """Refresh all enabled adapter config files with current state summary.

    Returns the number of files refreshed.
    """
    from vibe_state.adapters.base import build_adapter_context
    from vibe_state.adapters.registry import get_adapter

    config = safe_load_config(vibe_dir)
    project_root = vibe_dir.parent
    ctx = build_adapter_context(project_root)

    total = 0
    for adapter_name in config.adapters.enabled:
        adapter = get_adapter(adapter_name)
        if adapter:
            emitted = adapter.emit(ctx)
            total += len(emitted)
    return total


def check_dangerous_directory(cwd: Path | None = None) -> None:
    """Warn if running in HOME or root directory. Accepts cwd for testability."""
    resolved = (cwd or Path.cwd()).resolve()
    dangerous = [Path.home().resolve(), Path("/").resolve()]
    if resolved in dangerous:
        console.print(
            "[bold red]Warning:[/] You are in your HOME or root directory.\n"
            "Running vibe init here will pollute this directory with .vibe/ files.\n"
            "Please cd into a project directory first."
        )
        raise typer.Exit(1)

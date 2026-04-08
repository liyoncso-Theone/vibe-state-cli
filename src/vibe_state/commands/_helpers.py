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


def extract_latest_progress(content: str) -> str:
    """Extract the most recent Sync block or progress summary from current.md."""
    lines = content.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("## Sync") or lines[i].startswith("## Final Sync"):
            header = lines[i].strip()
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and not lines[j].startswith("```"):
                    return f"{header} — {lines[j].strip()}"
            return header
    in_progress = False
    for line in lines:
        if "Progress" in line and line.startswith("#"):
            in_progress = True
            continue
        if in_progress and line.strip() and not line.startswith("#"):
            return line.strip()
    return "(no progress recorded yet)"


def extract_section_items(content: str, section_name: str) -> list[str]:
    """Extract bullet items under a specific ## section."""
    lines = content.splitlines()
    in_section = False
    items: list[str] = []
    for line in lines:
        if line.startswith("## ") and section_name in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.strip().startswith("- "):
            item = line.strip()
            if item != "- (none)":
                items.append(item)
    return items


def sanitize_name(name: str) -> str:
    """Sanitize a project/adapter name: strip newlines, #, and control chars."""
    return "".join(c for c in name if c.isprintable() and c not in "\n\r#")


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

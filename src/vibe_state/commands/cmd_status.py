"""vibe status command."""

from __future__ import annotations

import typer
from rich.panel import Panel
from rich.table import Table

from vibe_state.commands._helpers import (
    app,
    console,
    get_vibe_dir,
)


@app.command()
def status() -> None:
    """Show current project state summary (available in any lifecycle state)."""
    from vibe_state.config import load_config
    from vibe_state.core.lifecycle import read_state
    from vibe_state.core.state import get_file_line_count, read_state_file

    vibe_dir = get_vibe_dir()

    if not vibe_dir.exists():
        console.print("[yellow]No .vibe/ directory found.[/] Run [bold]vibe init[/] first.")
        raise typer.Exit(1)

    lifecycle = read_state(vibe_dir)
    config = load_config(vibe_dir)

    # Count tasks
    tasks_content = read_state_file(vibe_dir, "tasks.md")
    task_lines = tasks_content.splitlines()
    pending = sum(1 for ln in task_lines if ln.strip().startswith("- [ ]"))
    done = sum(1 for ln in task_lines if ln.strip().startswith("- [x]"))
    stale = sum(1 for ln in task_lines if ln.strip().startswith("- [~]"))

    # File sizes
    file_lines: dict[str, int] = {}
    for fname in ["current.md", "tasks.md", "standards.md", "architecture.md", "archive.md"]:
        file_lines[fname] = get_file_line_count(vibe_dir, fname)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Lifecycle", lifecycle.value)
    table.add_row("Language", config.vibe.lang)
    table.add_row("Adapters", ", ".join(config.adapters.enabled))
    table.add_row("Git", "enabled" if config.git.enabled else "disabled")
    table.add_row("Tasks", f"{pending} pending, {done} done, {stale} stale")
    table.add_row("", "")
    table.add_row("File lines", "")
    for fname, lines in file_lines.items():
        marker = " [yellow](!)[/]" if lines > config.state.compact_threshold else ""
        table.add_row("", f"  {fname}: {lines}{marker}")

    console.print()
    console.print(Panel(table, title="[bold]vibe status[/]"))

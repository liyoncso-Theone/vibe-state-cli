"""vibe sync command."""

from __future__ import annotations

from datetime import datetime, timezone

import typer
from rich.panel import Panel

from vibe_state.commands._helpers import (
    app,
    append_progress_note,
    console,
    get_vibe_dir,
    perform_git_sync,
    refresh_adapters,
    require_lifecycle,
)


@app.command()
def sync(
    note: str = typer.Option(
        "",
        "--note",
        "-n",
        help="Append a semantic progress note to current.md (the 'why' behind commits).",
    ),
    no_refresh: bool = typer.Option(
        False,
        "--no-refresh",
        help="Skip adapter file refresh. Used by the git hook to avoid working-tree noise.",
    ),
    compact: bool = typer.Option(False, help="Run memory compaction after sync"),
    close: bool = typer.Option(False, help="Close project: final sync + compact + retrospective"),
) -> None:
    """Sync state from git. Use --note for rationale, --compact to archive, --close to end."""
    from vibe_state.config import load_config
    from vibe_state.core.compactor import compact_tasks
    from vibe_state.core.git_ops import git_available
    from vibe_state.core.lifecycle import write_state
    from vibe_state.core.state import append_to_state_file, write_state_file

    vibe_dir = get_vibe_dir()

    if close:
        next_state = require_lifecycle(get_vibe_dir(), "close")
    else:
        require_lifecycle(get_vibe_dir(), "sync")

    config = load_config(vibe_dir)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    # ── Semantic progress note (independent of git activity) ──
    if note:
        append_progress_note(vibe_dir, note)
        console.print(f"[green]Note added:[/] {note}")

    # ── Git sync (shared with `vibe start` auto-sync) ──
    has_changes = False
    if config.git.enabled and git_available():
        label = "Final Sync" if close else "Sync"
        result = perform_git_sync(vibe_dir, label=label)
        if result.commits_synced > 0:
            has_changes = True
            console.print(
                f"[green]Synced:[/] {result.commits_synced} commits"
                f" appended to state/current.md"
            )
            if result.experiments_kept or result.experiments_reverted:
                console.print(
                    f"[cyan]Experiments:[/] {result.experiments_kept} kept,"
                    f" {result.experiments_reverted} reverted"
                )
        elif close:
            # Close path always writes a sync block, even with no new commits
            append_to_state_file(
                vibe_dir, "current.md",
                f"\n## Final Sync [{now}]\n(No new commits since last sync.)\n",
            )
            has_changes = True
        else:
            console.print("[dim]No changes since last sync.[/]")
    else:
        append_to_state_file(
            vibe_dir, "current.md",
            f"\n## Sync [{now}]\n(No git — please update manually)\n",
        )
        console.print("[yellow]No git available.[/] Manual sync block appended.")

    # ── Compact (if --compact or --close) ──
    if compact or close:
        compact_result = compact_tasks(vibe_dir, stale_days=config.state.stale_task_days)
        console.print(
            f"[green]Compacted:[/] {compact_result.archived_tasks} tasks archived,"
            f" current.md {compact_result.current_before_lines}"
            f" → {compact_result.current_after_lines} lines"
        )

    # ── Close (if --close) ──
    if close:
        retro = (
            f"# Project Retrospective\n\n"
            f"Generated: {now}\n\n"
            f"## Deliverables\n\n- [Fill in major deliverables]\n\n"
            f"## Key Technical Decisions\n\n- [Fill in decisions and rationale]\n\n"
            f"## Remaining Items\n\n- [Unfinished features, known bugs, tech debt]\n\n"
            f"## Lessons Learned\n\n- [Best practices to carry forward]\n"
        )
        write_state_file(vibe_dir, "retrospective.md", retro)
        write_state(vibe_dir, next_state)
        refresh_adapters(vibe_dir)
        console.print(Panel(
            "Final sync + compact completed.\n"
            "Retrospective template: state/retrospective.md\n"
            "Project is now [bold]CLOSED[/].\n\n"
            "[dim]Use [bold]vibe init --force[/bold] to reopen.[/dim]",
            title="[bold]vibe sync --close[/]",
        ))
        return

    # ── Refresh adapter files with latest state summary ──
    if not no_refresh:
        count = refresh_adapters(vibe_dir)
        if count:
            console.print(f"[dim]Refreshed {count} adapter file(s).[/]")

    # ── C.L.E.A.R. checklist (only when there were actual changes) ──
    if not has_changes:
        return
    console.print()
    console.print(Panel(
        "[C] Core Logic   — Is the core logic correct? Edge cases?\n"
        "[L] Layout       — Structure/naming follows standards.md?\n"
        "[E] Evidence     — Test output or API response as proof?\n"
        "[A] Access       — Any hardcoded secrets or permission holes?\n"
        "[R] Refactor     — Obvious tech debt or performance issues?",
        title="[bold]C.L.E.A.R. Review Checklist[/]",
    ))

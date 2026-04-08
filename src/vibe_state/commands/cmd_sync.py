"""vibe sync command."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.panel import Panel

from vibe_state.commands._helpers import (
    app,
    console,
    get_vibe_dir,
    refresh_adapters,
    require_lifecycle,
)


@app.command()
def sync(
    compact: bool = typer.Option(False, help="Run memory compaction after sync"),
    close: bool = typer.Option(False, help="Close project: final sync + compact + retrospective"),
) -> None:
    """Sync state from git. Use --compact to archive tasks, --close to end project."""
    from vibe_state.config import load_config
    from vibe_state.core.compactor import compact_tasks
    from vibe_state.core.git_ops import (
        detect_experiment_commits,
        get_diff_stat,
        get_head_hash,
        get_log_since,
        git_available,
        read_sync_cursor,
        write_sync_cursor,
    )
    from vibe_state.core.lifecycle import write_state
    from vibe_state.core.state import append_to_state_file, write_state_file

    vibe_dir = get_vibe_dir()

    if close:
        next_state = require_lifecycle(get_vibe_dir(), "close")
    else:
        require_lifecycle(get_vibe_dir(), "sync")

    config = load_config(vibe_dir)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    # ── Git sync ──
    has_changes = False
    if config.git.enabled and git_available():
        root = Path.cwd()
        last_sync = read_sync_cursor(vibe_dir)
        commits = get_log_since(root, last_sync)
        diff_stat = get_diff_stat(root, last_sync)
        head = get_head_hash(root)

        # Skip if nothing changed (avoid empty sync blocks)
        if not commits and not diff_stat and not close:
            console.print("[dim]No changes since last sync.[/]")
        else:
            has_changes = True
            label = "Final Sync" if close else "Sync"
            block_lines = [
                f"\n## {label} [{now}]",
                f"Commits: {len(commits)} since last sync",
            ]
            if commits:
                block_lines.append("```")
                for c in commits[:20]:
                    block_lines.append(c)
                if len(commits) > 20:
                    block_lines.append(f"... and {len(commits) - 20} more")
                block_lines.append("```")
            if diff_stat:
                block_lines.append(f"\nFiles changed:\n```\n{diff_stat}\n```")

            sync_block = "\n".join(block_lines) + "\n"
            append_to_state_file(vibe_dir, "current.md", sync_block)
            write_sync_cursor(vibe_dir, head)

            console.print(
                f"[green]Synced:[/] {len(commits)} commits appended to state/current.md"
            )

            # Detect autoresearch experiment commits (patterns from config)
            experiments = detect_experiment_commits(
                root, last_sync,
                commit_patterns=config.experiments.commit_patterns,
                revert_prefixes=config.experiments.revert_prefixes,
            )
            if experiments:
                kept = sum(1 for e in experiments if not e.is_revert)
                reverted = sum(1 for e in experiments if e.is_revert)
                summary = f"{len(experiments)} iterations ({kept} kept, {reverted} reverted)"
                exp_lines = [f"\n## Experiments [{now}]", f"Detected: {summary}", ""]
                for exp in experiments:
                    status = "REVERTED" if exp.is_revert else "KEPT"
                    exp_lines.append(f"- [{status}] `{exp.hash}` {exp.message}")
                exp_lines.append("")
                append_to_state_file(vibe_dir, "experiments.md", "\n".join(exp_lines) + "\n")
                console.print(f"[cyan]Experiments:[/] {kept} kept, {reverted} reverted")
    else:
        append_to_state_file(
            vibe_dir, "current.md",
            f"\n## Sync [{now}]\n(No git — please update manually)\n",
        )
        console.print("[yellow]No git available.[/] Manual sync block appended.")

    # ── Compact (if --compact or --close) ──
    if compact or close:
        result = compact_tasks(vibe_dir, stale_days=config.state.stale_task_days)
        console.print(
            f"[green]Compacted:[/] {result.archived_tasks} tasks archived, "
            f"current.md {result.current_before_lines} → {result.current_after_lines} lines"
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

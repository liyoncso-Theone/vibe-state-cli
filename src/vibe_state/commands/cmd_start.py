"""vibe start command."""

from __future__ import annotations

from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from vibe_state.commands._helpers import (
    app,
    console,
    ensure_internal_gitignore,
    extract_latest_progress,
    extract_section_items,
    get_vibe_dir,
    perform_git_sync,
    refresh_adapters,
    require_lifecycle,
)


@app.command()
def start() -> None:
    """Load state, auto-sync new commits, auto-compact, output status summary."""
    from vibe_state.config import load_config
    from vibe_state.core.compactor import compact_tasks
    from vibe_state.core.git_ops import get_status, git_available
    from vibe_state.core.lifecycle import write_state
    from vibe_state.core.state import (
        get_file_line_count,
        read_state_file,
        validate_state_dir,
    )

    vibe_dir = get_vibe_dir()
    next_state = require_lifecycle(get_vibe_dir(), "start")

    # Self-healing upgrade: existing projects from older vibe versions may
    # be missing newly-introduced .gitignore entries (e.g. state/.hook.log
    # added in v0.3.4). Idempotent — no-op when already up-to-date.
    import contextlib

    with contextlib.suppress(OSError):
        ensure_internal_gitignore(vibe_dir)

    config = load_config(vibe_dir)

    # Validate state files exist
    missing = validate_state_dir(vibe_dir)
    if missing:
        console.print(f"[yellow]Warning:[/] Missing state files: {', '.join(missing)}")

    # Auto-sync: pull any new commits since last sync into state.
    # This makes `vibe sync` optional — start always loads a current state.
    auto_sync = perform_git_sync(vibe_dir, label="Sync")
    if auto_sync.commits_synced > 0:
        console.print(
            f"[green]Auto-synced:[/] {auto_sync.commits_synced} new commits"
            f" since last session"
        )
        if auto_sync.experiments_kept or auto_sync.experiments_reverted:
            console.print(
                f"[cyan]Experiments:[/] {auto_sync.experiments_kept} kept,"
                f" {auto_sync.experiments_reverted} reverted"
            )

    # Auto-compact if any file exceeds threshold
    threshold = config.state.compact_threshold
    for fname in ["current.md", "tasks.md", "standards.md", "architecture.md"]:
        lines = get_file_line_count(vibe_dir, fname)
        if lines > threshold:
            console.print(
                f"[yellow]Auto-compacting:[/] {fname} has {lines} lines (>{threshold})"
            )
            compact_tasks(vibe_dir, stale_days=config.state.stale_task_days)
            break

    # Git validation
    git_info = ""
    if config.git.enabled and git_available():
        changed = get_status(Path.cwd())
        git_info = f"{len(changed)} uncommitted changes" if changed else "clean"
    elif not config.git.enabled:
        git_info = "disabled"
    else:
        git_info = "git not found"

    # Read current state for summary
    current = read_state_file(vibe_dir, "current.md")
    tasks = read_state_file(vibe_dir, "tasks.md")

    # Extract latest progress: find last "## Sync" or "## Progress" block
    progress = extract_latest_progress(current)

    # Extract open issues (lines starting with "- " under "## Open Issues")
    open_issues = extract_section_items(current, "Open Issues")

    # Extract top 3 pending tasks
    pending: list[str] = []
    for line in tasks.splitlines():
        if line.strip().startswith("- [ ]") and len(pending) < 3:
            pending.append(line.strip().removeprefix("- [ ]").strip())

    # Extract experiment summary
    experiments = read_state_file(vibe_dir, "experiments.md")
    exp_summary = ""
    if experiments:
        kept = experiments.count("[KEPT]")
        reverted = experiments.count("[REVERTED]")
        if kept or reverted:
            exp_summary = f"{kept} kept, {reverted} reverted"

    write_state(vibe_dir, next_state)

    # Refresh adapter files with latest state summary
    refresh_adapters(vibe_dir)

    # Output Rich summary
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Progress", progress)
    table.add_row("Git", git_info)
    table.add_row(
        "Open issues",
        "\n".join(open_issues) if open_issues else "(none)",
    )
    if pending:
        table.add_row("Top tasks", "")
        for i, task in enumerate(pending, 1):
            table.add_row("", f"  {i}. {task}")
    else:
        table.add_row("Top tasks", "(none)")
    if exp_summary:
        table.add_row("Experiments", exp_summary)

    console.print()
    console.print(Panel(table, title="[bold]vibe start[/]", subtitle="Session loaded"))

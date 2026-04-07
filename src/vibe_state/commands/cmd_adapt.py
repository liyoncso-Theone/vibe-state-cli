"""vibe adapt command."""

from __future__ import annotations

from pathlib import Path

import typer

from vibe_state.commands._helpers import (
    app,
    console,
    get_vibe_dir,
    require_lifecycle,
)


@app.command()
def adapt(
    add: str | None = typer.Option(None, help="Add an adapter (e.g., claude, cursor)"),
    remove: str | None = typer.Option(None, help="Remove an adapter"),
    list_adapters: bool = typer.Option(False, "--list", help="List enabled adapters"),
    sync_adapters: bool = typer.Option(False, "--sync", help="Re-sync all adapter files"),
    confirm: bool = typer.Option(False, help="Confirm destructive operations"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
) -> None:
    """Manage AI/IDE adapter files."""
    from vibe_state.adapters.registry import get_adapter
    from vibe_state.config import load_config, save_config

    vibe_dir = get_vibe_dir()
    require_lifecycle(get_vibe_dir(), "adapt")

    config = load_config(vibe_dir)

    if list_adapters:
        from vibe_state.adapters.registry import get_all_adapter_names

        all_names = sorted(get_all_adapter_names())
        enabled = set(config.adapters.enabled)
        console.print("[bold]Adapters:[/]")
        for name in all_names:
            mark = "[green]ON [/]" if name in enabled else "[dim]OFF[/]"
            console.print(f"  {mark}  {name}")
        return

    if add:
        from vibe_state.adapters.registry import get_all_adapter_names

        valid_names = get_all_adapter_names()
        if add not in valid_names:
            console.print(
                f"[red]Error:[/] Unknown adapter '{add}'.\n"
                f"Available: {', '.join(valid_names)}"
            )
            raise typer.Exit(1)
        if add in config.adapters.enabled:
            console.print(f"[yellow]{add} is already enabled.[/]")
            return
        config.adapters.enabled.append(add)
        save_config(vibe_dir, config)
        console.print(f"[green]Added adapter:[/] {add}")
        console.print("[dim]Run [bold]vibe adapt --sync[/bold] to generate config files.[/dim]")
        return

    if remove:
        if remove not in config.adapters.enabled:
            console.print(f"[yellow]{remove} is not enabled.[/]")
            return
        adapter = get_adapter(remove)
        if not adapter:
            console.print(f"[red]Unknown adapter:[/] {remove}")
            return
        files_to_remove = adapter.clean(Path.cwd())
        if dry_run:
            console.print(f"[dim]Would remove adapter:[/] {remove}")
            for f in files_to_remove:
                console.print(f"  [dim]- {f.relative_to(Path.cwd())}[/]")
            console.print("[dim](dry-run, no files changed)[/]")
            return
        if not confirm:
            from vibe_state.safety import has_user_modifications

            modified = has_user_modifications(vibe_dir, remove, files_to_remove)
            if modified:
                console.print("[yellow]Warning:[/] These files have been manually edited:")
                for f in modified:
                    console.print(f"  - {f.relative_to(Path.cwd())}")
            console.print(
                f"[yellow]This will remove {len(files_to_remove)} file(s) for {remove}.[/]\n"
                f"Use [bold]--confirm[/bold] to execute or [bold]--dry-run[/bold] to preview."
            )
            return

        # Execute removal with backup
        from vibe_state.safety import create_backup

        if files_to_remove:
            backup_dir = create_backup(vibe_dir, remove, files_to_remove)
            for f in files_to_remove:
                f.unlink(missing_ok=True)
            console.print(f"[green]Removed {len(files_to_remove)} file(s) for {remove}[/]")
            console.print(f"[dim]Backup: {backup_dir.relative_to(Path.cwd())}[/]")
        config.adapters.enabled.remove(remove)
        save_config(vibe_dir, config)
        return

    if sync_adapters:
        from vibe_state.adapters.base import build_adapter_context
        from vibe_state.safety import has_user_modifications, save_snapshot

        ctx = build_adapter_context(Path.cwd())
        total_files = 0
        for adapter_name in config.adapters.enabled:
            adapter = get_adapter(adapter_name)
            if not adapter:
                console.print(f"[yellow]Unknown adapter:[/] {adapter_name}")
                continue
            existing_files = adapter.clean(Path.cwd())
            modified = has_user_modifications(vibe_dir, adapter_name, existing_files)
            if modified and not confirm:
                msg = "files modified by user, use --confirm to overwrite"
                console.print(f"[yellow]{adapter_name}:[/] {msg}")
                for f in modified:
                    console.print(f"  - {f.relative_to(Path.cwd())}")
                continue
            emitted = adapter.emit(ctx)
            save_snapshot(vibe_dir, adapter_name, emitted)
            total_files += len(emitted)
            console.print(f"[green]{adapter_name}:[/] {len(emitted)} file(s) synced")
        console.print(f"\n[bold]Total:[/] {total_files} adapter file(s) synced.")
        return

    console.print("[yellow]Specify --add, --remove, --list, or --sync.[/]")

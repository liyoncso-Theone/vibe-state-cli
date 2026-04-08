"""vibe init command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from vibe_state.commands._helpers import (
    app,
    check_dangerous_directory,
    console,
    get_vibe_dir,
    require_lifecycle,
    sanitize_name,
)


@app.command()
def init(
    lang: str = typer.Option("en", help="Template language: en, zh-TW"),
    force: bool = typer.Option(False, help="Force reinitialize (also reopens closed projects)"),
) -> None:
    """Initialize .vibe/ directory in the current project."""
    check_dangerous_directory()
    vibe_dir = get_vibe_dir()

    if (vibe_dir / "state" / ".lifecycle").exists() and not force:
        console.print("[yellow]Warning:[/] .vibe/ already exists. Use --force to reinitialize.")
        raise typer.Exit(1)

    # H1: Backup existing .vibe/ before --force overwrite
    if force and vibe_dir.exists():
        from vibe_state.safety import create_backup

        existing_files = list(vibe_dir.glob("*.md")) + list(vibe_dir.glob("state/*.md"))
        if existing_files:
            backup_dir = create_backup(vibe_dir, "_reinit", existing_files)
            console.print(f"[dim]Backed up existing .vibe/ to {backup_dir.name}[/]")

    if not force:
        require_lifecycle(get_vibe_dir(), "init")

    # Validate language
    from vibe_state.core.templates import SUPPORTED_LANGS

    if lang not in SUPPORTED_LANGS:
        console.print(
            f"[yellow]Warning:[/] '{lang}' is not a supported language. "
            f"Supported: {', '.join(sorted(SUPPORTED_LANGS))}. Falling back to 'en'."
        )
        lang = "en"

    # Phase 1: Scan project
    from vibe_state.core.scanner import scan_project

    console.print("[bold]Scanning project...[/]")
    scan = scan_project(Path.cwd())

    # Phase 2: Detect adapters or default
    selected_adapters = scan.detected_tools.copy()
    if not selected_adapters:
        selected_adapters = ["agents_md"]
        console.print(
            "[dim]No AI tools detected. Defaulting to AGENTS.md (universal standard).[/]"
        )

    if "agents_md" not in selected_adapters:
        selected_adapters.append("agents_md")

    # Phase 2.5: Migrate existing AI config files
    from vibe_state.core.migrator import build_imported_standards, scan_legacy_files

    migration = scan_legacy_files(Path.cwd())
    legacy_cleanup: list[Path] = []

    if migration.found_files:
        console.print(
            f"\n[cyan]Found {len(migration.found_files)} existing config file(s):[/]"
        )
        for f in migration.found_files:
            console.print(f"  - {f.relative_to(Path.cwd())}")

        if migration.extracted_rules:
            console.print(
                f"[cyan]Imported {migration.total_lines_imported} rules"
                f" into .vibe/state/standards.md[/]"
            )

        legacy_cleanup = migration.found_files.copy()

    # Phase 3: Render templates
    from vibe_state.config import VibeConfig, save_config
    from vibe_state.core.lifecycle import LifecycleState, write_state
    from vibe_state.core.templates import render_all_state_files

    config = VibeConfig()
    config.vibe.lang = lang
    config.adapters.enabled = selected_adapters
    config.git.enabled = scan.has_git

    files = render_all_state_files(
        languages=scan.languages,
        frameworks=scan.frameworks,
        project_name=sanitize_name(Path.cwd().name),
        stale_task_days=config.state.stale_task_days,
        lang=lang,
    )

    # Append imported rules to standards.md template
    if migration.extracted_rules:
        imported_section = build_imported_standards(migration.extracted_rules)
        standards_key = "state/standards.md"
        if standards_key in files:
            files[standards_key] = files[standards_key].rstrip() + "\n" + imported_section

    # Phase 4: Write files
    for rel_path, content in files.items():
        full_path = vibe_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8", newline="\n")

    save_config(vibe_dir, config)
    write_state(vibe_dir, LifecycleState.READY)

    # Write internal .gitignore for backups
    internal_gitignore = vibe_dir / ".gitignore"
    if not internal_gitignore.exists():
        internal_gitignore.write_text(
            "# vibe-state-cli internals (do not commit)\nbackups/\n",
            encoding="utf-8",
            newline="\n",
        )

    # Phase 5: Emit adapter files
    from vibe_state.adapters.base import build_adapter_context
    from vibe_state.adapters.registry import get_adapter

    ctx = build_adapter_context(Path.cwd())
    # Tell adapters which files belong to the user (don't overwrite)
    ctx.user_owned_files = [
        str(f.relative_to(Path.cwd())) for f in migration.found_files
    ]
    adapter_files: list[str] = []
    for adapter_name in selected_adapters:
        adapter = get_adapter(adapter_name)
        if adapter:
            emitted = adapter.emit(ctx)
            adapter_files.extend(str(f.relative_to(Path.cwd())) for f in emitted)

    # Summary
    console.print()
    adapter_summary = (
        "\n".join(f"  - {f}" for f in adapter_files) if adapter_files else "  (none)"
    )
    console.print(Panel.fit(
        f"[bold green].vibe/ initialized successfully![/]\n\n"
        f"Languages: {', '.join(scan.languages) or 'none detected'}\n"
        f"Frameworks: {', '.join(scan.frameworks) or 'none detected'}\n"
        f"Git: {'yes' if scan.has_git else 'no'}\n"
        f"Adapters: {', '.join(selected_adapters)}\n\n"
        f"Generated files:\n{adapter_summary}\n\n"
        f"[dim]Tip: commit .vibe/ to git so your team shares the same brain.[/dim]\n"
        f"[dim]Next: run [bold]vibe start[/bold] to begin your session.[/dim]",
        title="vibe init",
    ))

    # Offer to clean up legacy files (now that everything is in .vibe/)
    if legacy_cleanup:
        console.print()
        console.print(
            "[yellow]The following legacy config files have been imported"
            " into .vibe/ and are no longer needed:[/]"
        )
        for f in legacy_cleanup:
            console.print(f"  - {f.relative_to(Path.cwd())}")
        console.print(
            "\n[dim]You can safely delete them. Their rules now live in"
            " .vibe/state/standards.md.[/dim]"
            "\n[dim]Run: [bold]vibe adapt --sync[/bold] to regenerate"
            " adapter files from .vibe/ source.[/dim]"
        )

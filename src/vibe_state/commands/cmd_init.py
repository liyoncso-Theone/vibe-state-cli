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
    install_post_commit_hook,
    require_lifecycle,
    sanitize_name,
)


@app.command()
def init(
    lang: str = typer.Option("en", help="Template language: en, zh-TW"),
    force: bool = typer.Option(False, help="Force reinitialize (also reopens closed projects)"),
    no_hooks: bool = typer.Option(
        False,
        "--no-hooks",
        help="Skip git post-commit hook installation (auto-sync after every commit).",
    ),
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

    # Track files that remain in place — adapters must not overwrite these
    preserved_files: list[Path] = []

    if migration.found_files:
        import shutil

        # Per-file decision: files with extracted rules get archived, others preserved
        to_archive = [f for f in migration.found_files if f not in migration.files_without_rules]
        to_preserve = migration.files_without_rules.copy()

        # Warn about files we couldn't extract rules from
        if to_preserve:
            console.print(
                f"[bold yellow]Warning:[/] Could not extract rules from "
                f"{len(to_preserve)} file(s) (no `- bullet` lines found):"
            )
            for f in to_preserve:
                console.print(f"  - {f.relative_to(Path.cwd())} — preserved, migrate manually")
            preserved_files = to_preserve

        # Two-phase archive for files with extracted rules
        if to_archive:
            archive_dir = vibe_dir / "archive" / "legacy"
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Phase A: Copy all
            copied: list[tuple[Path, Path]] = []
            for f in to_archive:
                dest = archive_dir / f.relative_to(Path.cwd())
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                copied.append((f, dest))

            # Phase B: Verify
            all_ok = all(
                d.exists() and d.stat().st_size == s.stat().st_size
                for s, d in copied
            )

            # Phase C: Unlink only after verification
            if all_ok:
                for src, _dest in copied:
                    src.unlink()
                console.print(
                    f"[green]Archived {len(copied)} legacy file(s)"
                    f" to .vibe/archive/legacy/[/]"
                )
            else:
                console.print(
                    "[yellow]Warning:[/] Archive verification failed. "
                    "Originals preserved."
                )
                preserved_files.extend(to_archive)

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
    ctx.user_owned_files = [
        str(f.relative_to(Path.cwd())) for f in preserved_files
    ]
    adapter_files: list[str] = []
    for adapter_name in selected_adapters:
        adapter = get_adapter(adapter_name)
        if adapter:
            emitted = adapter.emit(ctx)
            adapter_files.extend(str(f.relative_to(Path.cwd())) for f in emitted)

    # Phase 6: Install git post-commit hook (auto-sync) unless opted out.
    # VIBE_SKIP_HOOK_INSTALL is honored so test suites can disable side effects
    # without changing every test invocation.
    import os

    hook_line = ""
    skip_hook = no_hooks or os.environ.get("VIBE_SKIP_HOOK_INSTALL")
    if not skip_hook and scan.has_git:
        hook_status = install_post_commit_hook(Path.cwd())
        if hook_status in ("installed", "appended"):
            hook_line = (
                "\n[dim]Git hook installed: every commit auto-syncs state."
                " Disable with `--no-hooks`.[/dim]"
            )
        elif hook_status == "already":
            hook_line = "\n[dim]Git hook already present.[/dim]"

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
        f"Generated files:\n{adapter_summary}{hook_line}\n\n"
        f"[dim]Tip: commit .vibe/ to git so your team shares the same brain.[/dim]\n"
        f"[dim]Next: run [bold]vibe start[/bold] to begin your session.[/dim]",
        title="vibe init",
    ))


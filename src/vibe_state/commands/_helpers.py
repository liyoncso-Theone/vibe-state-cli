"""Shared helpers for CLI commands. Dependency-injected via `vibe_dir` parameter."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibe_state.config import VibeConfig

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


def safe_load_config(vibe_dir: Path) -> VibeConfig:
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


# ── Git post-commit hook (auto-sync) ──

_HOOK_MARKER_START = "# vibe-state-cli:auto-sync"
_HOOK_MARKER_END = "# vibe-state-cli:auto-sync:end"

_HOOK_BLOCK = f"""\
{_HOOK_MARKER_START}
# Auto-installed by `vibe init`. Keeps state/current.md in sync with git.
# To disable, delete this block (between the start/end markers) or run
# `vibe init --force --no-hooks`. Failures are logged silently and never
# block your commit.
if command -v vibe >/dev/null 2>&1 && [ -d .vibe ]; then
  vibe sync --no-refresh >> .vibe/state/.hook.log 2>&1 || true
fi
{_HOOK_MARKER_END}
"""


def install_post_commit_hook(project_root: Path) -> str:
    """Install or update the git post-commit hook for auto-sync.

    Idempotent: if the vibe block is already present, no-op.
    Returns: "installed" / "appended" / "already" / "no_git".
    """
    git_dir = project_root / ".git"
    if not git_dir.is_dir():
        return "no_git"

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "post-commit"

    status: str
    if hook_path.exists():
        try:
            existing = hook_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            existing = ""
        if _HOOK_MARKER_START in existing:
            return "already"
        new_content = existing.rstrip() + "\n\n" + _HOOK_BLOCK
        status = "appended"
    else:
        new_content = "#!/usr/bin/env sh\n" + _HOOK_BLOCK
        status = "installed"

    hook_path.write_text(new_content, encoding="utf-8", newline="\n")

    # Make executable on POSIX. Windows (git-for-windows) ignores this gracefully.
    try:
        import stat

        hook_path.chmod(
            hook_path.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
    except (OSError, NotImplementedError):
        pass

    return status


def append_progress_note(vibe_dir: Path, note: str) -> None:
    """Append a dated semantic note to the Progress Summary section of current.md.

    Note is inserted at the end of the Progress Summary section (recognizes both
    English "Progress Summary" and zh-TW "進度摘要" headings). If no such section
    exists, one is created at the end of the file.

    The note captures architectural intent / rationale that git commit messages
    alone don't preserve — the "why" behind a series of commits.
    """
    from datetime import datetime, timezone

    from vibe_state.core.state import read_state_file, write_state_file

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_line = f"{date} — {note}"

    content = read_state_file(vibe_dir, "current.md")
    if not content.strip():
        write_state_file(
            vibe_dir,
            "current.md",
            f"# Current State\n\n## Progress Summary\n\n{new_line}\n",
        )
        return

    lines = content.splitlines()
    progress_start: int | None = None
    for i, line in enumerate(lines):
        stripped = line.lstrip("#").strip()
        if stripped in ("Progress Summary", "進度摘要"):
            progress_start = i
            break

    if progress_start is None:
        lines.extend(["", "## Progress Summary", "", new_line])
        write_state_file(vibe_dir, "current.md", "\n".join(lines) + "\n")
        return

    # Find next ## heading after the progress section
    insert_at = len(lines)
    for j in range(progress_start + 1, len(lines)):
        if lines[j].startswith("## "):
            insert_at = j
            break

    # Trim trailing blank lines from the progress section before inserting
    while insert_at > progress_start + 1 and lines[insert_at - 1].strip() == "":
        insert_at -= 1

    lines.insert(insert_at, new_line)
    lines.insert(insert_at + 1, "")
    write_state_file(vibe_dir, "current.md", "\n".join(lines) + "\n")


@dataclass
class SyncResult:
    """Outcome of a git → state sync. All fields are 0/empty when no-op."""

    commits_synced: int = 0
    experiments_kept: int = 0
    experiments_reverted: int = 0


def perform_git_sync(vibe_dir: Path, *, label: str = "Sync") -> SyncResult:
    """Append git activity to state/current.md, update sync cursor, detect experiments.

    Idempotent: returns SyncResult() (all zeros) if state already current.
    Used by both `vibe sync` and `vibe start` (auto-sync) to keep state fresh.
    """
    from datetime import datetime, timezone

    from vibe_state.core.git_ops import (
        detect_experiment_commits,
        get_diff_stat,
        get_head_hash,
        get_log_since,
        git_available,
        read_sync_cursor,
        write_sync_cursor,
    )
    from vibe_state.core.state import append_to_state_file

    result = SyncResult()
    config = safe_load_config(vibe_dir)
    if not config.git.enabled or not git_available():
        return result

    project_root = vibe_dir.parent
    last_sync = read_sync_cursor(vibe_dir)
    commits = get_log_since(project_root, last_sync)
    diff_stat = get_diff_stat(project_root, last_sync)

    if not commits and not diff_stat:
        return result

    head = get_head_hash(project_root)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

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

    append_to_state_file(vibe_dir, "current.md", "\n".join(block_lines) + "\n")
    write_sync_cursor(vibe_dir, head)
    result.commits_synced = len(commits)

    # Detect autoresearch experiment commits
    experiments = detect_experiment_commits(
        project_root,
        last_sync,
        commit_patterns=config.experiments.commit_patterns,
        revert_prefixes=config.experiments.revert_prefixes,
    )
    if experiments:
        kept = sum(1 for e in experiments if not e.is_revert)
        reverted = sum(1 for e in experiments if e.is_revert)
        result.experiments_kept = kept
        result.experiments_reverted = reverted
        summary = f"{len(experiments)} iterations ({kept} kept, {reverted} reverted)"
        exp_lines = [f"\n## Experiments [{now}]", f"Detected: {summary}", ""]
        for exp in experiments:
            status_label = "REVERTED" if exp.is_revert else "KEPT"
            exp_lines.append(f"- [{status_label}] `{exp.hash}` {exp.message}")
        exp_lines.append("")
        append_to_state_file(
            vibe_dir, "experiments.md", "\n".join(exp_lines) + "\n"
        )

    return result


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

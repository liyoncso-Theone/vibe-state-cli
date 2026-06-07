"""Shared helpers for CLI commands. Dependency-injected via `vibe_dir` parameter."""

from __future__ import annotations

import logging
import shutil
import subprocess
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


def _version_callback(value: bool) -> None:
    """Typer callback for --version flag."""
    if value:
        from vibe_state import __version__

        typer.echo(f"vibe-state-cli {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="vibe",
    help="Model-agnostic AI-human collaboration state management CLI.",
    no_args_is_help=True,
)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
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


# ── Internal .gitignore management ──

# Files that vibe writes at runtime and must never be committed.
# Keep this list in sync with what hook scripts and atomic writes produce.
#
# v0.3.6: .sync-cursor and .lifecycle moved here. Both are machine-driven
# state (cursor mutates on every commit, lifecycle on every state transition);
# tracking them in git created the infinite "modified after every commit"
# loop because the post-commit hook re-wrote them after the commit landed.
# Treat them like ~/.claude/projects/<hash>/*.jsonl — runtime state stays
# on disk, never in the index.
_INTERNAL_GITIGNORE_ENTRIES: tuple[str, ...] = (
    "backups/",
    "state/*.lock",
    "state/.hook.log",
    "state/.sync-cursor",
    "state/.lifecycle",
)

# Files that v0.3.6 migration moves from tracked to untracked. Used by
# ensure_state_files_untracked() to surgically `git rm --cached` only the
# files that semantically became runtime state, leaving user-content files
# (current.md, tasks.md, standards.md, etc.) tracked.
_FILES_TO_UNTRACK_V0_3_6: tuple[str, ...] = (
    ".vibe/state/.sync-cursor",
    ".vibe/state/.lifecycle",
)


def ensure_internal_gitignore(vibe_dir: Path) -> tuple[bool, list[str]]:
    """Make sure .vibe/.gitignore covers every runtime artifact vibe produces.

    Idempotent: if the file is missing, it's written from a template.
    If it exists, we append only the entries that aren't already present —
    user-added lines are preserved untouched.

    Returns: (was_changed, entries_added)
    """
    gi_path = vibe_dir / ".gitignore"

    if not gi_path.exists():
        gi_path.parent.mkdir(parents=True, exist_ok=True)
        body = "# vibe-state-cli internals (do not commit)\n" + "\n".join(
            _INTERNAL_GITIGNORE_ENTRIES
        ) + "\n"
        gi_path.write_text(body, encoding="utf-8", newline="\n")
        return True, list(_INTERNAL_GITIGNORE_ENTRIES)

    try:
        existing = gi_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False, []

    existing_lines = {ln.strip() for ln in existing.splitlines()}
    missing = [e for e in _INTERNAL_GITIGNORE_ENTRIES if e not in existing_lines]
    if not missing:
        return False, []

    # Avoid a stray leading newline when the existing file is empty or
    # whitespace-only (rstrip() == "").
    prefix = existing.rstrip()
    new_content = (prefix + "\n" if prefix else "") + "\n".join(missing) + "\n"
    gi_path.write_text(new_content, encoding="utf-8", newline="\n")
    return True, missing


# ── Git post-commit hook (auto-sync) ──

_HOOK_MARKER_START = "# vibe-state-cli:auto-sync"
_HOOK_MARKER_END = "# vibe-state-cli:auto-sync:end"

# Hook runs sync in a backgrounded subshell so the commit prompt returns
# immediately even on big repos where `vibe sync` takes several seconds.
# `(... &)` is POSIX-portable and works under git-bash on Windows.
_HOOK_BLOCK = f"""\
{_HOOK_MARKER_START}
# Auto-installed by `vibe init`. Keeps .sync-cursor advanced to HEAD on
# every commit (current.md is reserved for explicit `vibe sync` /
# `vibe start` so this hook never creates a tracked-file write loop).
# Runs in background so your commit prompt is never blocked.
# To disable, delete this block (between the start/end markers) or run
# `vibe init --force --no-hooks`. Failures are logged silently to
# .vibe/state/.hook.log and never block your commit.
if command -v vibe >/dev/null 2>&1 && [ -d .vibe ]; then
  (vibe sync --no-refresh >> .vibe/state/.hook.log 2>&1 &) >/dev/null 2>&1 || true
fi
{_HOOK_MARKER_END}
"""


def _resolve_git_dir(project_root: Path) -> Path | None:
    """Resolve the actual git directory for project_root.

    Handles three cases:
    - `.git` is a directory (normal repo): return it.
    - `.git` is a file containing `gitdir: <path>` (submodule or
      linked worktree): follow the gitdir: pointer and return the resolved
      path. Hooks installed there fire correctly for the submodule's
      post-commit. Worktrees share core hooks with the main checkout, but
      git still respects per-worktree hook dirs when present.
    - `.git` missing or unreadable: return None.
    """
    git_path = project_root / ".git"
    if git_path.is_dir():
        return git_path
    if not git_path.is_file():
        return None
    try:
        text = git_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("gitdir:"):
            target = line.removeprefix("gitdir:").strip()
            target_path = Path(target)
            if not target_path.is_absolute():
                target_path = (project_root / target_path).resolve()
            return target_path if target_path.is_dir() else None
    return None


def install_post_commit_hook(project_root: Path) -> str:
    """Install or update the git post-commit hook for auto-sync.

    Idempotent: if the vibe block is already present, no-op.
    Resolves gitlinks (submodules / linked worktrees) so the hook lands
    in the right per-checkout hooks dir.
    Returns: "installed" / "appended" / "already" / "no_git".
    """
    git_dir = _resolve_git_dir(project_root)
    if git_dir is None:
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


def perform_cursor_update(vibe_dir: Path) -> SyncResult:
    """Lightweight sync: update only `.sync-cursor` to HEAD.

    v0.3.6: this is what the post-commit hook calls. It deliberately does
    NOT touch `current.md`, because writing to a tracked file from the hook
    creates an infinite `git status` loop (hook fires → file becomes
    "modified" → user commits → hook fires again → loop).

    `current.md` is reserved for user-initiated syncs (`vibe sync` no flag,
    `vibe start`) so explicit human action is what populates the
    human-readable activity log.

    Returns SyncResult with commits_synced reflecting the gap closed by
    this cursor advance (purely informational; the file is not written).
    """
    from vibe_state.core.git_ops import (
        get_head_hash,
        get_log_since,
        git_available,
        read_sync_cursor,
        write_sync_cursor,
    )

    result = SyncResult()
    config = safe_load_config(vibe_dir)
    if not config.git.enabled or not git_available():
        return result

    project_root = vibe_dir.parent
    last_sync = read_sync_cursor(vibe_dir)
    commits = get_log_since(project_root, last_sync)

    if not commits:
        return result

    head = get_head_hash(project_root)
    write_sync_cursor(vibe_dir, head)
    result.commits_synced = len(commits)
    return result


def perform_git_sync(vibe_dir: Path, *, label: str = "Sync") -> SyncResult:
    """Full sync: append git activity to state/current.md, update cursor,
    detect experiments.

    Called by explicit `vibe sync` and `vibe start` (user-initiated). The
    post-commit hook calls `perform_cursor_update()` instead — see that
    function's docstring for why.

    Idempotent: returns SyncResult() (all zeros) if state already current.
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


def ensure_state_files_untracked(project_root: Path) -> list[str]:
    """v0.3.6 migration: move `.sync-cursor` and `.lifecycle` out of the git
    index for projects that originally tracked them.

    Idempotent. File contents stay on disk; only the index entry is removed
    via `git rm --cached`. Called from `vibe init --force` and `vibe start`
    so existing projects upgrade silently on next session start.

    Returns the list of paths actually untracked (empty if all clean).
    """
    git_dir = _resolve_git_dir(project_root)
    if git_dir is None:
        return []

    untracked: list[str] = []
    for rel in _FILES_TO_UNTRACK_V0_3_6:
        # `git ls-files --error-unmatch` exits 0 if tracked, 1 if not.
        try:
            check = subprocess.run(
                ["git", "ls-files", "--error-unmatch", rel],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if check.returncode != 0:
            continue
        try:
            rm = subprocess.run(
                ["git", "rm", "--cached", "--quiet", rel],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if rm.returncode == 0:
                untracked.append(rel)
        except (OSError, subprocess.TimeoutExpired):
            continue
    return untracked


def _extract_latest_sync_block(current_md: str) -> str:
    """Pull the most recent `## Sync [...]` block out of current.md as a
    standalone string. Used by `vibe sync --promote` as the pre-fill for
    the human to edit before shipping.

    Returns empty string if no sync block found.
    """
    lines = current_md.splitlines()
    last_start: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("## Sync ") or line.startswith("## Final Sync "):
            last_start = i
    if last_start is None:
        return ""
    end = len(lines)
    for j in range(last_start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[last_start:end]).rstrip() + "\n"


def promote_to_backend(
    vibe_dir: Path,
    title: str,
    *,
    editor_factory: object = None,
) -> tuple[bool, str]:
    """v0.3.6: promote the most recent sync block to an external knowledge
    store via vendor-neutral subprocess call.

    Architecture:
        - `target` config is a string (today: "basic-memory"; future:
          "obsidian", "logseq", "raw-file", ...).
        - Each recognized target maps to a subprocess command shape.
          Unknown targets surface an actionable error pointing at
          .vibe/config.toml.
        - On `enabled = False`, returns (False, "promotion disabled")
          without side effect.
        - Failure modes (binary not on PATH, subprocess non-zero) return
          friendly errors; never raise.

    `editor_factory` is for testing — pass a callable that returns the
    final note content without launching $EDITOR. Production code leaves
    it None, which opens the user's editor with the latest sync block
    pre-filled.

    Returns: (success, message).
    """
    import os
    import tempfile

    from vibe_state.core.state import read_state_file

    config = safe_load_config(vibe_dir)
    if not config.promotion.enabled:
        return False, (
            "Promotion disabled. Set [promotion].enabled = true in"
            " .vibe/config.toml to use --promote."
        )

    title = (title or "").strip()
    if not title:
        return False, "Promotion requires a title (--promote 'short title')."

    current_md = read_state_file(vibe_dir, "current.md")
    pre_fill = _extract_latest_sync_block(current_md)
    if not pre_fill:
        pre_fill = (
            f"# {title}\n\n_(No recent sync block found; edit and add the\n"
            f"rationale you want promoted.)_\n"
        )
    else:
        pre_fill = (
            f"# {title}\n\n"
            "<!-- Edit this down to the rationale you want to promote.\n"
            "     Everything below this comment is the latest sync block;\n"
            "     keep, trim, or rewrite as needed. Save & close to ship. -->\n\n"
            f"{pre_fill}"
        )

    # Get the edited content
    if editor_factory is not None:
        # Test path: caller supplies the final content directly.
        edited = editor_factory(pre_fill) if callable(editor_factory) else str(editor_factory)
    else:
        editor = os.environ.get("EDITOR") or (
            "notepad" if os.name == "nt" else "vi"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(pre_fill)
            tmp_path = tmp.name
        try:
            ret = subprocess.run([editor, tmp_path])
            if ret.returncode != 0:
                return False, f"Editor {editor!r} exited non-zero; aborting promotion."
            with open(tmp_path, encoding="utf-8") as f:
                edited = f.read()
        finally:
            import contextlib

            with contextlib.suppress(OSError):
                os.unlink(tmp_path)

    edited = edited.strip()
    if not edited:
        return False, "Empty content after edit; nothing promoted."

    # ── Dispatch by target ──
    target = config.promotion.target
    if target == "basic-memory":
        if shutil.which("basic-memory") is None:
            return False, (
                "basic-memory CLI not found on PATH. Install it from"
                " https://docs.basicmemory.com/ or change [promotion].target"
                " in .vibe/config.toml."
            )
        try:
            ret = subprocess.run(
                [
                    "basic-memory", "tool", "write-note",
                    "--project", config.promotion.project,
                    "--folder", config.promotion.folder,
                    "--title", title,
                ],
                input=edited,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, f"basic-memory invocation failed: {e}"
        if ret.returncode != 0:
            err = (ret.stderr or "").strip() if isinstance(ret.stderr, str) else ""
            out = (ret.stdout or "").strip() if isinstance(ret.stdout, str) else ""
            return False, (
                f"basic-memory exited {ret.returncode}: {err or out}"
            )
        return True, (
            f"Promoted to {target}:{config.promotion.project}/{config.promotion.folder}: {title!r}"
        )

    return False, (
        f"Unknown promotion target {target!r}. Set [promotion].target in"
        " .vibe/config.toml to one of: basic-memory."
    )


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

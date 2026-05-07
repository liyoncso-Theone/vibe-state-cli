"""vibe status command — health dashboard with staleness awareness."""

from __future__ import annotations

import time
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from vibe_state.commands._helpers import (
    app,
    console,
    get_vibe_dir,
)

# ── i18n: status command messages ──
# Local to cmd_status.py until another command needs i18n (then extract).

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "no_vibe_dir": "[yellow]No .vibe/ directory found.[/] Run [bold]vibe init[/] first.",
        "lifecycle": "Lifecycle",
        "last_sync": "Last sync",
        "last_sync_today": "today ({commits} commits behind)",
        "last_sync_today_clean": "today (state is current)",
        "last_sync_recent": "{days} days ago ({commits} commits behind)",
        "last_sync_recent_clean": "{days} days ago (state is current)",
        "last_sync_never": "never synced",
        "last_sync_no_git": "(git disabled)",
        "state_health": "State health",
        "health_fresh": "[green]FRESH[/]",
        "health_stale": "[yellow]STALE[/] — run `vibe sync`",
        "health_very_stale": "[red]VERY STALE[/] — run `vibe sync` urgently",
        "health_no_git": "(git disabled — manual updates only)",
        "adapter_sync": "Adapter sync",
        "adapter_fresh": "[green]✓ fresh[/]",
        "adapter_stale": "[yellow]⚠ stale[/]",
        "adapter_missing": "[red]✗ missing[/]",
        "adapter_user_owned": "[dim](user-owned)[/]",
        "git": "Git",
        "git_enabled": "enabled",
        "git_disabled": "disabled",
        "git_unavailable": "not available",
        "language": "Content lang",
        "tasks": "Tasks",
        "tasks_value": "{pending} pending, {done} done, {stale} stale",
        "file_lines": "File lines",
    },
    "zh-TW": {
        "no_vibe_dir": "[yellow]找不到 .vibe/ 目錄。[/] 請先執行 [bold]vibe init[/]。",
        "lifecycle": "生命週期",
        "last_sync": "上次同步",
        "last_sync_today": "今天（落後 {commits} 個 commit）",
        "last_sync_today_clean": "今天（狀態最新）",
        "last_sync_recent": "{days} 天前（落後 {commits} 個 commit）",
        "last_sync_recent_clean": "{days} 天前（狀態最新）",
        "last_sync_never": "尚未同步",
        "last_sync_no_git": "（git 已停用）",
        "state_health": "狀態健康度",
        "health_fresh": "[green]新鮮[/]",
        "health_stale": "[yellow]過期[/] — 請執行 `vibe sync`",
        "health_very_stale": "[red]嚴重過期[/] — 建議立即執行 `vibe sync`",
        "health_no_git": "（git 已停用，僅能手動更新）",
        "adapter_sync": "Adapter 同步",
        "adapter_fresh": "[green]✓ 新鮮[/]",
        "adapter_stale": "[yellow]⚠ 過期[/]",
        "adapter_missing": "[red]✗ 不存在[/]",
        "adapter_user_owned": "[dim](使用者自有)[/]",
        "git": "Git",
        "git_enabled": "已啟用",
        "git_disabled": "已停用",
        "git_unavailable": "未安裝",
        "language": "內容語言",
        "tasks": "任務",
        "tasks_value": "{pending} 待辦, {done} 完成, {stale} 過期",
        "file_lines": "檔案行數",
    },
}


def _t(key: str, lang: str, **kwargs: object) -> str:
    """Translate a message key, falling back to en if missing."""
    table = _MESSAGES.get(lang, _MESSAGES["en"])
    msg = table.get(key) or _MESSAGES["en"].get(key, key)
    return msg.format(**kwargs) if kwargs else msg


def _days_since(path: Path) -> int | None:
    """Return integer days since path's mtime, or None if path missing."""
    if not path.exists():
        return None
    delta = time.time() - path.stat().st_mtime
    return max(0, int(delta // 86400))


def _classify_health(days: int, commits_behind: int) -> str:
    """Return health key: fresh / stale / very_stale."""
    if days >= 14 or commits_behind > 30:
        return "very_stale"
    if days >= 3 or commits_behind >= 5:
        return "stale"
    return "fresh"


def _check_adapter_freshness(vibe_dir: Path, adapter_name: str) -> str:
    """Return status key: fresh / stale / missing / user_owned.

    Adapters often write multiple files (e.g., claude writes CLAUDE.md +
    .claude/rules/*.md + skills). Some files inject the state summary,
    others don't (CLAUDE.md uses `@AGENTS.md` and stays small). An adapter
    is "fresh" if ANY of its managed files contains the current summary
    marker; "stale" if managed files exist but none contain it.
    """
    from vibe_state.adapters.registry import get_adapter
    from vibe_state.core.summary import build_state_summary

    project_root = vibe_dir.parent
    adapter = get_adapter(adapter_name)
    if adapter is None:
        return "missing"

    files = adapter.clean(project_root)
    if not files:
        return "missing"

    # Collect all managed files
    managed_contents: list[str] = []
    for f in files:
        if f.suffix not in (".md", ".mdc"):
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "<!-- vibe-state-cli:managed -->" in content:
            managed_contents.append(content)

    if not managed_contents:
        return "user_owned"

    # If state has nothing to inject, presence of managed files is enough.
    summary = build_state_summary(vibe_dir)
    if not summary.strip():
        return "fresh"

    summary_lines = summary.splitlines()
    summary_marker = summary_lines[0] if summary_lines else ""
    if not summary_marker:
        return "fresh"

    # Fresh if any managed file carries the current summary marker.
    for content in managed_contents:
        if summary_marker in content:
            return "fresh"
    return "stale"


@app.command()
def status() -> None:
    """Show project state health: lifecycle, sync staleness, adapter sync state."""
    from vibe_state.config import load_config
    from vibe_state.core.git_ops import get_log_since, git_available, read_sync_cursor
    from vibe_state.core.lifecycle import read_state
    from vibe_state.core.state import get_file_line_count, read_state_file

    vibe_dir = get_vibe_dir()

    if not vibe_dir.exists():
        console.print(_t("no_vibe_dir", "en"))
        raise typer.Exit(1)

    lifecycle = read_state(vibe_dir)
    config = load_config(vibe_dir)
    lang = config.vibe.lang if config.vibe.lang in _MESSAGES else "en"
    project_root = vibe_dir.parent

    # ── Sync staleness ──
    cursor_path = vibe_dir / "state" / ".sync-cursor"
    last_sync_hash = read_sync_cursor(vibe_dir)
    git_on = config.git.enabled and git_available()

    days_since_sync: int | None = None
    commits_behind: int | None = None

    if git_on:
        if last_sync_hash:
            days_since_sync = _days_since(cursor_path)
            commits_behind = len(get_log_since(project_root, last_sync_hash))
        else:
            lifecycle_path = vibe_dir / "state" / ".lifecycle"
            days_since_sync = _days_since(lifecycle_path)

    # ── Format Last sync line + State health ──
    if not git_on:
        last_sync_text = _t("last_sync_no_git", lang)
        health_text = _t("health_no_git", lang)
    elif not last_sync_hash:
        last_sync_text = _t("last_sync_never", lang)
        # Treat "never synced" with old init as stale
        days_init = days_since_sync or 0
        health_key = "health_stale" if days_init >= 3 else "health_fresh"
        health_text = _t(health_key, lang)
    else:
        days = days_since_sync or 0
        commits = commits_behind or 0
        if days == 0:
            key = "last_sync_today_clean" if commits == 0 else "last_sync_today"
        else:
            key = "last_sync_recent_clean" if commits == 0 else "last_sync_recent"
        last_sync_text = _t(key, lang, days=days, commits=commits)
        health_text = _t(f"health_{_classify_health(days, commits)}", lang)

    # ── Adapter sync state ──
    adapter_rows: list[tuple[str, str]] = []
    for name in config.adapters.enabled:
        status_key = _check_adapter_freshness(vibe_dir, name)
        marker = _t(f"adapter_{status_key}", lang)
        adapter_rows.append((name, marker))

    # ── Tasks ──
    tasks_content = read_state_file(vibe_dir, "tasks.md")
    task_lines = tasks_content.splitlines()
    pending = sum(1 for ln in task_lines if ln.strip().startswith("- [ ]"))
    done = sum(1 for ln in task_lines if ln.strip().startswith("- [x]"))
    stale_tasks = sum(1 for ln in task_lines if ln.strip().startswith("- [~]"))

    # ── Git status ──
    if not config.git.enabled:
        git_text = _t("git_disabled", lang)
    elif git_available():
        git_text = _t("git_enabled", lang)
    else:
        git_text = _t("git_unavailable", lang)

    # ── File lines (kept, deprioritized) ──
    file_lines: dict[str, int] = {}
    for fname in ["current.md", "tasks.md", "standards.md", "architecture.md", "archive.md"]:
        file_lines[fname] = get_file_line_count(vibe_dir, fname)

    # ── Render ──
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()

    table.add_row(_t("lifecycle", lang), lifecycle.value)
    table.add_row(_t("last_sync", lang), last_sync_text)
    table.add_row(_t("state_health", lang), health_text)

    if adapter_rows:
        table.add_row(_t("adapter_sync", lang), "")
        max_name_len = max(len(n) for n, _ in adapter_rows)
        for name, marker in adapter_rows:
            table.add_row("", f"  {name.ljust(max_name_len)}  {marker}")

    table.add_row(_t("git", lang), git_text)
    table.add_row(_t("language", lang), config.vibe.lang)
    table.add_row(
        _t("tasks", lang),
        _t("tasks_value", lang, pending=pending, done=done, stale=stale_tasks),
    )

    table.add_row("", "")
    table.add_row(_t("file_lines", lang), "")
    for fname, lines in file_lines.items():
        marker = " [yellow](!)[/]" if lines > config.state.compact_threshold else ""
        table.add_row("", f"  {fname}: {lines}{marker}")

    console.print()
    console.print(Panel(table, title="[bold]vibe status[/]"))

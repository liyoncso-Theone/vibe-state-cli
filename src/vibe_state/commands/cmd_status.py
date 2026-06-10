"""vibe status command — health dashboard with staleness awareness.

v0.3.8: also exposes `vibe status --diagnose` for deep environment checks
(brew-doctor style — Environment / Project / Adapters / Memory layer).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from vibe_state.commands._helpers import (
    app,
    console,
    get_vibe_dir,
)

# v0.3.8 diagnose: per-check subprocess timeout. The original RFC trigger
# (BM cold-start ≥30s on Windows) is the worst-case; 5s captures
# "daemon healthy on warm cache" without hanging the diagnose pipeline.
_DIAGNOSE_TIMEOUT = 5

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


# ── v0.3.8: diagnose ──


@dataclass
class _CheckResult:
    """A single diagnose check's outcome.

    `status` is one of: "ok" / "warn" / "error". Only `error` causes the
    diagnose pipeline to exit non-zero (brew-doctor convention — warnings
    are informational, not fatal).
    """

    status: str
    message: str
    fix_hint: str | None = None


def _check_environment() -> list[_CheckResult]:
    """vibe binary on PATH, python version, pipx healthy."""
    import shutil
    import subprocess
    import sys

    results: list[_CheckResult] = []

    bin_path = shutil.which("vibe")
    if bin_path:
        try:
            v = subprocess.run(
                [bin_path, "--version"],
                capture_output=True, text=True, timeout=_DIAGNOSE_TIMEOUT,
            )
            if v.returncode == 0:
                version_line = (v.stdout or "").strip() or "(no version output)"
                results.append(_CheckResult(
                    "ok", f"vibe binary: {bin_path} ({version_line})"
                ))
            else:
                results.append(_CheckResult(
                    "warn",
                    f"vibe binary at {bin_path}, `--version` exited {v.returncode}",
                ))
        except subprocess.TimeoutExpired:
            results.append(_CheckResult(
                "warn",
                f"vibe binary probe timed out (>{_DIAGNOSE_TIMEOUT}s)",
            ))
        except OSError as e:
            results.append(_CheckResult("warn", f"vibe binary check failed: {e}"))
    else:
        results.append(_CheckResult(
            "error", "vibe binary not on PATH",
            "Reinstall: `pipx install --force vibe-state-cli`",
        ))

    # pyproject enforces python>=3.10 at install, but report the actual
    # version for operator context (helps debug "wrong venv" issues).
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    results.append(_CheckResult("ok", f"python: {py_ver}"))

    pipx_path = shutil.which("pipx")
    if pipx_path:
        results.append(_CheckResult("ok", f"pipx: {pipx_path}"))
    else:
        results.append(_CheckResult(
            "warn", "pipx not on PATH",
            "Optional, but recommended for clean isolated installs",
        ))

    return results


def _check_project(vibe_dir: Path, project_root: Path) -> list[_CheckResult]:
    """`.vibe/` structure, config readability, gitignore entries, post-commit hook."""
    from vibe_state.commands._helpers import (
        _HOOK_MARKER_START,
        _INTERNAL_GITIGNORE_ENTRIES,
        _resolve_git_dir,
    )
    from vibe_state.config import ConfigParseError, load_config

    results: list[_CheckResult] = []

    state_dir = vibe_dir / "state"
    if state_dir.is_dir():
        results.append(_CheckResult("ok", ".vibe/state/ structure: present"))
    else:
        results.append(_CheckResult(
            "error", ".vibe/state/ missing", "Run `vibe init`",
        ))
        return results

    config_path = vibe_dir / "config.toml"
    if config_path.exists():
        try:
            load_config(vibe_dir)
            results.append(_CheckResult("ok", "config.toml: readable"))
        except ConfigParseError as e:
            results.append(_CheckResult(
                "error", f"config.toml parse error: {e}",
                "Fix or delete .vibe/config.toml and re-run `vibe init`",
            ))
            return results
    else:
        results.append(_CheckResult(
            "warn", "config.toml missing — using built-in defaults",
        ))

    gi_path = vibe_dir / ".gitignore"
    if gi_path.exists():
        try:
            gi_content = gi_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            gi_content = ""
        gi_lines = {ln.strip() for ln in gi_content.splitlines()}
        missing = [e for e in _INTERNAL_GITIGNORE_ENTRIES if e not in gi_lines]
        if missing:
            results.append(_CheckResult(
                "warn", f".vibe/.gitignore missing entries: {', '.join(missing)}",
                "Run `vibe start` or `vibe init --force` to self-heal",
            ))
        else:
            results.append(_CheckResult("ok", ".vibe/.gitignore: all entries present"))
    else:
        results.append(_CheckResult(
            "warn", ".vibe/.gitignore missing",
            "Run `vibe start` to auto-create",
        ))

    git_dir = _resolve_git_dir(project_root)
    if git_dir is None:
        results.append(_CheckResult(
            "warn", "post-commit hook: not installed (no .git in project)",
        ))
    else:
        hook_path = git_dir / "hooks" / "post-commit"
        if hook_path.exists():
            try:
                hook_content = hook_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                hook_content = ""
            if _HOOK_MARKER_START in hook_content:
                results.append(_CheckResult("ok", "post-commit hook: installed"))
            else:
                results.append(_CheckResult(
                    "warn", "post-commit hook exists but no vibe-state-cli marker",
                    "Run `vibe init --force` to add vibe block",
                ))
        else:
            results.append(_CheckResult(
                "warn", "post-commit hook: not installed",
                "Run `vibe init --force` to install (skip with `--no-hooks`)",
            ))

    return results


def _check_adapters(vibe_dir: Path) -> list[_CheckResult]:
    """Each enabled adapter's freshness + AGENTS.md has Persistent Knowledge."""
    from vibe_state.config import load_config

    results: list[_CheckResult] = []

    try:
        config = load_config(vibe_dir)
    except Exception:
        results.append(_CheckResult(
            "warn", "Skipping adapter checks (config unreadable)",
        ))
        return results

    if not config.adapters.enabled:
        results.append(_CheckResult(
            "warn", "No adapters enabled in config.toml",
        ))
        return results

    project_root = vibe_dir.parent
    for name in config.adapters.enabled:
        status_key = _check_adapter_freshness(vibe_dir, name)
        if status_key == "fresh":
            results.append(_CheckResult("ok", f"{name}: fresh"))
        elif status_key == "stale":
            results.append(_CheckResult(
                "warn", f"{name}: stale (state summary out of sync)",
                "Run `vibe sync` to regenerate adapter files",
            ))
        elif status_key == "missing":
            results.append(_CheckResult(
                "error", f"{name}: managed files missing",
                f"Run `vibe adapt --sync` to regenerate {name} files",
            ))
        elif status_key == "user_owned":
            results.append(_CheckResult(
                "ok", f"{name}: user-owned (no managed marker — intentional)",
            ))
        else:
            results.append(_CheckResult("warn", f"{name}: unknown state ({status_key})"))

    # v0.3.7 Persistent Knowledge section check — agents_md only
    if "agents_md" in config.adapters.enabled:
        agents_md = project_root / "AGENTS.md"
        if agents_md.exists():
            try:
                content = agents_md.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                # Silent-pass here used to hide cross-machine determinism
                # differences (one machine readable, another not → different
                # check counts in Summary). Surface it as a warning so the
                # user has feedback AND the count is consistent.
                results.append(_CheckResult(
                    "warn", f"AGENTS.md: unreadable ({e})",
                    "Check file permissions or restore from backup",
                ))
            else:
                if "## Persistent Knowledge" in content:
                    results.append(_CheckResult(
                        "ok",
                        "AGENTS.md: contains Persistent Knowledge section"
                        " (v0.3.7+ template)",
                    ))
                else:
                    results.append(_CheckResult(
                        "warn",
                        "AGENTS.md: missing Persistent Knowledge section"
                        " (pre-v0.3.7 template)",
                        "Run `vibe sync` to regenerate with latest template",
                    ))

    return results


def _check_memory_layer(vibe_dir: Path) -> list[_CheckResult]:
    """\\[memory].enabled + basic-memory CLI + MCP runtime probe."""
    import shutil
    import subprocess

    from vibe_state.config import load_config

    results: list[_CheckResult] = []

    try:
        config = load_config(vibe_dir)
        mem = config.memory
    except Exception:
        results.append(_CheckResult(
            "warn", "Skipping memory checks (config unreadable)",
        ))
        return results

    if not mem.enabled:
        results.append(_CheckResult(
            "ok", "\\[memory].enabled = false (memory layer disabled — no checks needed)",
        ))
        return results

    results.append(_CheckResult(
        "ok", f"\\[memory].enabled = true (target: {mem.target!r})",
    ))

    if mem.target != "basic-memory":
        results.append(_CheckResult(
            "warn",
            f"\\[memory].target = {mem.target!r} — diagnose only knows basic-memory",
            "Manual check required for this target; future versions may add support",
        ))
        return results

    bm = shutil.which("basic-memory")
    if not bm:
        results.append(_CheckResult(
            "error", "basic-memory CLI not on PATH",
            "Install: https://docs.basicmemory.com/ or flip \\[memory].enabled = false",
        ))
        return results

    results.append(_CheckResult("ok", f"basic-memory CLI: {bm}"))

    # Runtime probe — invoke basic-memory --version with hard timeout. This
    # confirms the binary spawns + responds without hanging (the original
    # SessionStart-hook failure mode the v0.3.7 RFC was filed against was
    # exactly basic-memory taking >30s to respond on Windows cold start).
    try:
        r = subprocess.run(
            [bm, "--version"],
            capture_output=True, text=True, timeout=_DIAGNOSE_TIMEOUT,
        )
        if r.returncode == 0:
            v_text = (r.stdout or "").strip().splitlines()
            v_first = v_text[0] if v_text else "(no output)"
            results.append(_CheckResult(
                "ok", f"basic-memory runtime probe: {v_first}",
            ))
        else:
            results.append(_CheckResult(
                "warn",
                f"basic-memory --version exited {r.returncode}",
                "Daemon may be misconfigured — check basic-memory logs",
            ))
    except subprocess.TimeoutExpired:
        results.append(_CheckResult(
            "warn",
            f"basic-memory runtime probe timed out (>{_DIAGNOSE_TIMEOUT}s)",
            "Daemon may be cold-starting; first query is often slow on Windows."
            " Retry in 30s; if it persists, restart basic-memory.",
        ))
    except OSError as e:
        results.append(_CheckResult(
            "error", f"basic-memory runtime probe failed: {e}",
        ))

    return results


def _render_diagnose_group(title: str, results: list[_CheckResult]) -> None:
    """brew-doctor style group rendering."""
    console.print(f"\n[bold cyan]\\[{title}][/]")
    for r in results:
        marker = {
            "ok": "[green]✓[/]",
            "warn": "[yellow]⚠[/]",
            "error": "[red]✗[/]",
        }.get(r.status, "?")
        console.print(f"  {marker} {r.message}")
        if r.fix_hint:
            console.print(f"    [dim]→ {r.fix_hint}[/]")


def _run_diagnose(vibe_dir: Path) -> int:
    """Run all 4 diagnose check groups + render + return exit code."""
    project_root = vibe_dir.parent

    env_results = _check_environment()
    project_results = _check_project(vibe_dir, project_root)
    adapter_results = _check_adapters(vibe_dir)
    memory_results = _check_memory_layer(vibe_dir)

    _render_diagnose_group("Environment", env_results)
    _render_diagnose_group("Project", project_results)
    _render_diagnose_group("Adapters", adapter_results)
    _render_diagnose_group("Memory layer", memory_results)

    all_results = env_results + project_results + adapter_results + memory_results
    n_ok = sum(1 for r in all_results if r.status == "ok")
    n_warn = sum(1 for r in all_results if r.status == "warn")
    n_error = sum(1 for r in all_results if r.status == "error")

    console.print(
        f"\n[bold]Summary:[/] [green]{n_ok} ok[/], "
        f"[yellow]{n_warn} warnings[/], [red]{n_error} errors[/]"
    )

    return 1 if n_error > 0 else 0


# ── status command (extended with --diagnose in v0.3.8) ──


@app.command()
def status(
    diagnose: bool = typer.Option(
        False,
        "--diagnose",
        help=(
            "Run deep environment diagnostics (brew-doctor style):"
            " Environment / Project / Adapters / Memory layer."
            " Exit 1 if any errors; warnings still exit 0."
        ),
    ),
) -> None:
    """Show project state health: lifecycle, sync staleness, adapter sync state.

    Use --diagnose for deep environment checks (PATH, MCP, adapters, etc).
    """
    from vibe_state.config import load_config
    from vibe_state.core.git_ops import get_log_since, git_available, read_sync_cursor
    from vibe_state.core.lifecycle import read_state
    from vibe_state.core.state import get_file_line_count, read_state_file

    vibe_dir = get_vibe_dir()

    if not vibe_dir.exists():
        console.print(_t("no_vibe_dir", "en"))
        raise typer.Exit(1)

    if diagnose:
        exit_code = _run_diagnose(vibe_dir)
        if exit_code != 0:
            raise typer.Exit(exit_code)
        return

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

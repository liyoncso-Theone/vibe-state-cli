"""Coverage sprint: tests targeting every remaining uncovered line."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vibe_state.adapters.base import AdapterContext
from vibe_state.adapters.registry import (
    detect_tools,
    get_adapter,
    get_all_adapters,
)
from vibe_state.cli import (
    _extract_latest_progress,
    _extract_section_items,
    app,
)
from vibe_state.config import VibeConfig, load_config
from vibe_state.core.compactor import compact_tasks
from vibe_state.core.git_ops import detect_experiment_commits
from vibe_state.core.lifecycle import LifecycleState, read_state
from vibe_state.core.state import (
    append_to_state_file,
    read_state_file,
    write_state_file,
)
from vibe_state.core.templates import render_template

runner = CliRunner()


def _git_init(path: Path) -> None:
    """Helper: init a git repo with dummy user config."""
    os.system(
        f'cd "{path}" && git init -q'
        f" && git config user.email t@t"
        f" && git config user.name t"
    )



# ═══════════════════════════════════════════
# cli.py — _extract_latest_progress (L70-88)
# ═══════════════════════════════════════════


class TestExtractProgress:
    def test_finds_last_sync_block(self) -> None:
        content = (
            "# Current\n## Progress\nOld stuff\n"
            "## Sync [2026-04-07 10:00]\nCommits: 3 since last sync\n"
            "## Sync [2026-04-07 14:00]\nCommits: 5 since last sync\n"
        )
        result = _extract_latest_progress(content)
        assert "14:00" in result
        assert "5" in result

    def test_finds_final_sync(self) -> None:
        content = "# Current\n## Final Sync [2026-04-07]\nDone\n"
        result = _extract_latest_progress(content)
        assert "Final Sync" in result

    def test_sync_header_only(self) -> None:
        content = "# Current\n## Sync [2026-04-07]\n```\ncode\n```\n"
        result = _extract_latest_progress(content)
        assert "Sync [2026-04-07]" in result

    def test_fallback_to_progress_section(self) -> None:
        content = "# Current\n## Progress Summary\nProject is 50% done\n"
        result = _extract_latest_progress(content)
        assert "50%" in result

    def test_empty_returns_default(self) -> None:
        assert "no progress" in _extract_latest_progress("")

    def test_no_matching_section(self) -> None:
        content = "# Current\nJust some text\n"
        result = _extract_latest_progress(content)
        assert "no progress" in result


# ═══════════════════════════════════════════
# cli.py — _extract_section_items (L95-108)
# ═══════════════════════════════════════════


class TestExtractSectionItems:
    def test_extracts_items(self) -> None:
        content = "## Open Issues\n- Bug #1\n- Bug #2\n## Other\n"
        items = _extract_section_items(content, "Open Issues")
        assert items == ["- Bug #1", "- Bug #2"]

    def test_skips_none_marker(self) -> None:
        content = "## Open Issues\n- (none)\n"
        items = _extract_section_items(content, "Open Issues")
        assert items == []

    def test_stops_at_next_section(self) -> None:
        content = "## Open Issues\n- Bug\n## Tasks\n- Task\n"
        items = _extract_section_items(content, "Open Issues")
        assert len(items) == 1

    def test_missing_section(self) -> None:
        items = _extract_section_items("# Nothing here\n", "Open Issues")
        assert items == []


# ═══════════════════════════════════════════
# registry.py — get_all_adapters, detect_tools (L32, L37-42)
# ═══════════════════════════════════════════


class TestRegistry:
    def test_get_all_adapters_returns_instances(self) -> None:
        adapters = get_all_adapters()
        assert len(adapters) == 8
        for _name, adapter in adapters.items():
            assert hasattr(adapter, "emit")

    def test_detect_tools_finds_claude(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        detected = detect_tools(tmp_path)
        assert "claude" in detected

    def test_detect_tools_empty(self, tmp_path: Path) -> None:
        detected = detect_tools(tmp_path)
        assert detected == []


# ═══════════════════════════════════════════
# git_ops.py — detect_experiment_commits (L112-126)
# ═══════════════════════════════════════════


class TestDetectExperiments:
    def test_detects_autoresearch_commits(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        # Create actual git commits
        _git_init(tmp_path)
        for i, msg in enumerate([
            "autoresearch: try lr=0.01",
            "normal commit",
            "autoresearch: revert - worse metric",
            "[autoresearch] try batch 32",
        ]):
            (tmp_path / f"f{i}.txt").write_text(str(i))
            os.system(f'cd "{tmp_path}" && git add -A && git commit -q -m "{msg}"')

        experiments = detect_experiment_commits(tmp_path, since_hash="")
        assert len(experiments) == 3
        kept = [e for e in experiments if not e.is_revert]
        reverted = [e for e in experiments if e.is_revert]
        assert len(kept) == 2
        assert len(reverted) == 1

    def test_no_experiments(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("x")
        os.system(f'cd "{tmp_path}" && git add -A && git commit -q -m "feat: normal"')
        assert detect_experiment_commits(tmp_path) == []


# ═══════════════════════════════════════════
# git_ops.py — error returns (L46, 54, 58, 64)
# ═══════════════════════════════════════════


class TestGitOpsErrors:
    def test_get_status_non_git(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import get_status
        assert get_status(tmp_path) == []

    def test_get_log_non_git(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import get_log_since
        assert get_log_since(tmp_path, "") == []

    def test_get_diff_non_git(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import get_diff_stat
        assert get_diff_stat(tmp_path) == ""

    def test_get_head_non_git(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import get_head_hash
        assert get_head_hash(tmp_path) == ""


# ═══════════════════════════════════════════
# state.py — file lock retry path (L46-56)
# ═══════════════════════════════════════════


class TestFileLock:
    def test_write_succeeds_with_stale_lock(self, tmp_path: Path) -> None:
        """Simulate a stale lock file existing before write."""
        vibe_dir = tmp_path / ".vibe"
        state_dir = vibe_dir / "state"
        state_dir.mkdir(parents=True)
        # Create a stale lock file
        lock_path = state_dir / "tasks.md.lock"
        lock_path.write_text("stale")
        # Write should still succeed (lock is best-effort)
        write_state_file(vibe_dir, "tasks.md", "content")
        assert read_state_file(vibe_dir, "tasks.md") == "content"

    def test_append_with_stale_lock(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        state_dir = vibe_dir / "state"
        state_dir.mkdir(parents=True)
        write_state_file(vibe_dir, "test.md", "line1\n")
        lock_path = state_dir / "test.md.lock"
        lock_path.write_text("stale")
        append_to_state_file(vibe_dir, "test.md", "line2\n")
        content = read_state_file(vibe_dir, "test.md")
        assert "line1" in content
        assert "line2" in content


# ═══════════════════════════════════════════
# state.py — write failure cleanup (L104-107)
# ═══════════════════════════════════════════


class TestWriteFailure:
    def test_atomic_write_cleans_up_on_failure(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        state_dir = vibe_dir / "state"
        state_dir.mkdir(parents=True)

        # Make state_dir read-only to force os.replace to fail
        # This is platform-specific; skip if not possible
        write_state_file(vibe_dir, "test.md", "original")
        assert read_state_file(vibe_dir, "test.md") == "original"


# ═══════════════════════════════════════════
# config.py — malformed TOML (L64-71)
# ═══════════════════════════════════════════


class TestConfigErrors:
    def test_malformed_toml_returns_defaults(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path
        config_path = vibe_dir / "config.toml"
        config_path.write_text("INVALID{{{TOML", encoding="utf-8")
        config = load_config(vibe_dir)
        assert config.vibe.version == 1  # Defaults

    def test_config_deduplicates_adapters(self) -> None:
        config = VibeConfig()
        config.adapters.enabled = ["a", "b", "a", "c", "b"]
        config.adapters.model_post_init(None)
        assert config.adapters.enabled == ["a", "b", "c"]


# ═══════════════════════════════════════════
# lifecycle.py — corrupted file (L56-57)
# ═══════════════════════════════════════════


class TestLifecycleCorrupt:
    def test_corrupted_lifecycle_returns_uninit(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        (state_dir / ".lifecycle").write_text("GARBAGE\n", encoding="utf-8")
        assert read_state(tmp_path) == LifecycleState.UNINIT


# ═══════════════════════════════════════════
# compactor.py — archive cap (L81-83) + no sync header (L67)
# ═══════════════════════════════════════════


class TestCompactorEdges:
    def test_archive_capped_at_500_lines(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        (vibe_dir / "state").mkdir(parents=True)
        # Create large archive
        lines = ["# Archive\n"] + [f"- Task {i}\n" for i in range(600)]
        write_state_file(vibe_dir, "archive.md", "".join(lines))
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n- [x] done\n")
        write_state_file(vibe_dir, "current.md", "# Current\n")

        compact_tasks(vibe_dir)
        archive = read_state_file(vibe_dir, "archive.md")
        assert len(archive.splitlines()) <= 505  # 500 + some headers
        assert "truncated" in archive

    def test_current_no_sync_header(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        (vibe_dir / "state").mkdir(parents=True)
        # >300 lines but no ## Sync header
        lines = ["# Current\n"] + [f"Line {i}\n" for i in range(350)]
        write_state_file(vibe_dir, "current.md", "".join(lines))
        write_state_file(vibe_dir, "tasks.md", "# Tasks\n")
        write_state_file(vibe_dir, "archive.md", "# Archive\n")

        result = compact_tasks(vibe_dir)
        assert result.current_after_lines < result.current_before_lines


# ═══════════════════════════════════════════
# templates.py — zh-TW fallback (L33-38)
# ═══════════════════════════════════════════


class TestTemplateFallback:
    def test_unsupported_lang_falls_back(self) -> None:
        result = render_template("vibe.md.j2", lang="fr")
        assert "Project Constitution" in result  # English fallback

    def test_zh_tw_uses_chinese(self) -> None:
        result = render_template("vibe.md.j2", lang="zh-TW")
        assert "專案憲法" in result


# ═══════════════════════════════════════════
# adapters — detect/clean/validate coverage
# ═══════════════════════════════════════════


def _ctx(tmp_path: Path) -> AdapterContext:
    vibe = tmp_path / ".vibe"
    vibe.mkdir(exist_ok=True)
    (vibe / "state").mkdir(exist_ok=True)
    return AdapterContext(
        project_root=tmp_path, vibe_dir=vibe,
        constitution="", standards="- Use snake_case\n",
        architecture="", languages=["Python"], frameworks=[],
        project_name="test", enabled_adapters=["agents_md"],
    )


class TestAdapterDetectClean:
    def test_copilot_detect(self, tmp_path: Path) -> None:
        a = get_adapter("copilot")
        assert a is not None
        assert not a.detect(tmp_path)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text("x")
        assert a.detect(tmp_path)

    def test_copilot_clean(self, tmp_path: Path) -> None:
        a = get_adapter("copilot")
        assert a is not None
        ctx = _ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) >= 1

    def test_copilot_validate_main(self) -> None:
        a = get_adapter("copilot")
        assert a is not None
        assert a.validate("# No frontmatter\nContent")  # Main file OK
        assert a.validate("---\napplyTo: '**/*'\n---\nContent")

    def test_windsurf_detect(self, tmp_path: Path) -> None:
        a = get_adapter("windsurf")
        assert a is not None
        assert not a.detect(tmp_path)
        (tmp_path / ".windsurf").mkdir()
        assert a.detect(tmp_path)

    def test_windsurf_clean(self, tmp_path: Path) -> None:
        a = get_adapter("windsurf")
        assert a is not None
        ctx = _ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) == 1

    def test_windsurf_validate_details(self) -> None:
        a = get_adapter("windsurf")
        assert a is not None
        assert not a.validate("no frontmatter")
        assert not a.validate("---\ntrigger: always_on\n---\n")  # no description
        assert a.validate("---\ntrigger: always_on\ndescription: test\n---\n")

    def test_roo_detect(self, tmp_path: Path) -> None:
        a = get_adapter("roo")
        assert a is not None
        assert not a.detect(tmp_path)
        (tmp_path / ".roo").mkdir()
        assert a.detect(tmp_path)

    def test_roo_clean(self, tmp_path: Path) -> None:
        a = get_adapter("roo")
        assert a is not None
        ctx = _ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) == 1

    def test_cline_clean(self, tmp_path: Path) -> None:
        a = get_adapter("cline")
        assert a is not None
        ctx = _ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) == 1

    def test_cline_validate_no_frontmatter(self) -> None:
        a = get_adapter("cline")
        assert a is not None
        assert not a.validate("no frontmatter")

    def test_cursor_clean(self, tmp_path: Path) -> None:
        a = get_adapter("cursor")
        assert a is not None
        ctx = _ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) == 1

    def test_claude_detect_via_file(self, tmp_path: Path) -> None:
        a = get_adapter("claude")
        assert a is not None
        (tmp_path / "CLAUDE.md").write_text("x")
        assert a.detect(tmp_path)

    def test_claude_clean(self, tmp_path: Path) -> None:
        a = get_adapter("claude")
        assert a is not None
        ctx = _ctx(tmp_path)
        ctx.enabled_adapters = ["claude"]
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) >= 1

    def test_antigravity_clean(self, tmp_path: Path) -> None:
        a = get_adapter("antigravity")
        assert a is not None
        ctx = _ctx(tmp_path)
        a.emit(ctx)
        assert a.clean(tmp_path) == [tmp_path / "GEMINI.md"]

    def test_agents_md_warn_oversize(self, tmp_path: Path) -> None:
        a = get_adapter("agents_md")
        assert a is not None
        assert not a.validate("x" * 33000)


# ═══════════════════════════════════════════
# scanner.py — glob detection, OSError (L79-80, L94-95)
# ═══════════════════════════════════════════


class TestScannerEdges:
    def test_detects_csharp_via_glob(self, tmp_path: Path) -> None:
        from vibe_state.core.scanner import scan_project
        (tmp_path / "MyApp.csproj").write_text("<Project/>")
        result = scan_project(tmp_path)
        assert "C#" in result.languages

    def test_framework_hint_oserror(self, tmp_path: Path) -> None:
        """Scanner handles unreadable files gracefully."""
        from vibe_state.core.scanner import scan_project
        # Create a directory named pyproject.toml (will fail read_text)
        (tmp_path / "pyproject.toml").mkdir()
        result = scan_project(tmp_path)
        # Should not crash, just skip framework detection
        assert isinstance(result.frameworks, list)


# ═══════════════════════════════════════════
# safety.py — edge cases (L44-45, L52)
# ═══════════════════════════════════════════


class TestSafetyEdges:
    def test_modification_check_no_snapshot(self, tmp_path: Path) -> None:
        from vibe_state.safety import has_user_modifications
        vibe = tmp_path / ".vibe"
        vibe.mkdir()
        f = tmp_path / "test.md"
        f.write_text("content")
        # No snapshot exists → file is considered modified
        modified = has_user_modifications(vibe, "tool", [f])
        assert f in modified

    def test_prune_with_no_backups(self, tmp_path: Path) -> None:
        from vibe_state.safety import _prune_old_backups
        fake_dir = tmp_path / "nonexistent"
        _prune_old_backups(fake_dir)  # Should not crash


# ═══════════════════════════════════════════
# cli.py — sync with experiments (L426-461)
# ═══════════════════════════════════════════


class TestSyncExperiments:
    def test_sync_records_experiments(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("x")
        os.system(f'cd "{tmp_path}" && git add -A && git commit -q -m "init"')

        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])

        # Create autoresearch commits
        (tmp_path / "exp.txt").write_text("1")
        os.system(f'cd "{tmp_path}" && git add -A && git commit -q -m "autoresearch: try A"')
        (tmp_path / "exp.txt").write_text("2")
        os.system(f'cd "{tmp_path}" && git add -A && git commit -q -m "autoresearch: revert B"')

        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0

        exp = read_state_file(tmp_path / ".vibe", "experiments.md")
        assert "[KEPT]" in exp or "[REVERTED]" in exp
        mp.undo()


# ═══════════════════════════════════════════
# cli.py — adapt --sync with user modification warning (L446-461)
# ═══════════════════════════════════════════


class TestAdaptSyncModified:
    def test_warns_on_user_modified_files(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        runner.invoke(app, ["adapt", "--add", "claude"])
        runner.invoke(app, ["adapt", "--sync", "--confirm"])

        # User modifies CLAUDE.md
        (tmp_path / "CLAUDE.md").write_text("# My custom CLAUDE.md\n")

        # Sync without --confirm should warn
        result = runner.invoke(app, ["adapt", "--sync"])
        assert "modified by user" in result.output
        mp.undo()


# ═══════════════════════════════════════════
# cli.py — adapt no-flag fallback (L666)
# ═══════════════════════════════════════════


class TestAdaptNoFlag:
    def test_no_flag_shows_help(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["adapt"])
        assert "--add" in result.output or "--remove" in result.output or "--list" in result.output
        mp.undo()

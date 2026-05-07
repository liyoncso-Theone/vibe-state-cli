"""CLI integration: full lifecycle, init/start/sync/status/adapt all scenarios."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from vibe_state.cli import app
from vibe_state.commands._helpers import extract_latest_progress, extract_section_items
from vibe_state.config import load_config, save_config
from vibe_state.core.lifecycle import LifecycleState, read_state
from vibe_state.core.state import read_state_file, write_state_file

runner = CliRunner()


def _git_init(p: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=p, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=p, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=p, capture_output=True)


# ── Full lifecycle ──


class TestCliFullLifecycle:
    def test_init_start_sync_close_reinit(self, tmp_path: Path) -> None:
        """Test: init -> start -> sync -> sync --compact -> sync --close -> init --force."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')

        # init
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".vibe" / "state" / ".lifecycle").exists()
        assert read_state(tmp_path / ".vibe") == LifecycleState.READY

        # init again should fail
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1

        # start
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0, result.output
        assert read_state(tmp_path / ".vibe") == LifecycleState.ACTIVE

        # status (always available)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0, result.output
        assert "ACTIVE" in result.output

        # sync (no commits yet)
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0, result.output
        assert "No changes" in result.output or "Synced" in result.output

        # sync --compact
        result = runner.invoke(app, ["sync", "--compact"])
        assert result.exit_code == 0, result.output
        assert "Compacted" in result.output

        # sync --close
        result = runner.invoke(app, ["sync", "--close"])
        assert result.exit_code == 0, result.output
        assert read_state(tmp_path / ".vibe") == LifecycleState.CLOSED
        assert (tmp_path / ".vibe" / "state" / "retrospective.md").exists()

        # sync after close should fail
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 1

        # init --force reopens
        result = runner.invoke(app, ["init", "--force"])
        assert result.exit_code == 0, result.output
        assert read_state(tmp_path / ".vibe") == LifecycleState.READY

        # start again should work
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0

        # sync should work again
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        monkeypatch.undo()

    def test_only_five_commands(self) -> None:
        """Verify CLI has exactly 5 commands."""
        commands = [cmd for cmd in app.registered_commands]
        command_names = {cmd.name or cmd.callback.__name__ for cmd in commands}
        assert command_names == {"init", "start", "sync", "status", "adapt"}


# ── Init scenarios ──


class TestCliInit:
    def test_root_directory_blocked(self) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir("/")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1
        mp.undo()

    def test_init_blocked_in_home(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(Path.home())
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1
        assert "HOME or root" in result.output
        monkeypatch.undo()

    def test_force_creates_backup(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        # Create a file that would trigger backup
        (tmp_path / ".vibe" / "state" / "current.md").write_text("# Custom\n")
        result = runner.invoke(app, ["init", "--force"])
        assert result.exit_code == 0
        assert "Backed up" in result.output
        monkeypatch.undo()

    def test_init_installs_post_commit_hook(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`vibe init` should install a post-commit hook that auto-syncs."""
        monkeypatch.delenv("VIBE_SKIP_HOOK_INSTALL", raising=False)
        monkeypatch.chdir(tmp_path)
        _git_init(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        assert hook.exists()
        content = hook.read_text(encoding="utf-8")
        assert "vibe-state-cli:auto-sync" in content
        assert "vibe sync --no-refresh" in content

    def test_init_no_hooks_skips_hook(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`vibe init --no-hooks` should NOT install the post-commit hook."""
        monkeypatch.delenv("VIBE_SKIP_HOOK_INSTALL", raising=False)
        monkeypatch.chdir(tmp_path)
        _git_init(tmp_path)
        result = runner.invoke(app, ["init", "--no-hooks"])
        assert result.exit_code == 0
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        assert not hook.exists()

    def test_init_hook_install_is_idempotent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Re-running init --force should not duplicate the hook block."""
        monkeypatch.delenv("VIBE_SKIP_HOOK_INSTALL", raising=False)
        monkeypatch.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["init", "--force"])
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        content = hook.read_text(encoding="utf-8")
        # Marker should appear exactly once
        assert content.count("vibe-state-cli:auto-sync\n") == 1

    def test_init_appends_to_existing_hook(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If post-commit already exists, init should append (not overwrite)."""
        monkeypatch.delenv("VIBE_SKIP_HOOK_INSTALL", raising=False)
        monkeypatch.chdir(tmp_path)
        _git_init(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        existing_hook = hooks_dir / "post-commit"
        existing_hook.write_text(
            "#!/usr/bin/env sh\necho 'user hook'\n", encoding="utf-8"
        )
        runner.invoke(app, ["init"])
        content = existing_hook.read_text(encoding="utf-8")
        assert "echo 'user hook'" in content  # Original preserved
        assert "vibe-state-cli:auto-sync" in content  # Vibe block appended

    def test_init_creates_internal_gitignore(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        gi = tmp_path / ".vibe" / ".gitignore"
        assert gi.exists()
        content = gi.read_text(encoding="utf-8")
        assert "backups/" in content
        monkeypatch.undo()

    def test_init_archives_legacy_files(self, tmp_path: Path) -> None:
        """vibe init should archive existing CLAUDE.md to .vibe/archive/legacy/."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        # Create a user-owned CLAUDE.md before init
        (tmp_path / "CLAUDE.md").write_text("# My Old Rules\n- Use TypeScript\n")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        # Old file archived
        archived = tmp_path / ".vibe" / "archive" / "legacy" / "CLAUDE.md"
        assert archived.exists()
        assert "My Old Rules" in archived.read_text(encoding="utf-8")
        # Old file removed from project root
        assert not (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").startswith("# My Old")
        # New CLAUDE.md generated by adapter (has managed marker)
        new_content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "vibe-state-cli:managed" in new_content
        # Rules imported into standards.md
        standards = (tmp_path / ".vibe" / "state" / "standards.md").read_text(encoding="utf-8")
        assert "Use TypeScript" in standards
        monkeypatch.undo()

    def test_init_warns_on_zero_rules(self, tmp_path: Path) -> None:
        """When legacy files have no bullet rules, warn and preserve originals."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        # Paragraph-style rules — no "- " bullets
        (tmp_path / "CLAUDE.md").write_text(
            "## Code Style\nUse snake_case for all variables.\n"
            "Always add type hints.\nRun pytest before committing.\n"
        )
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "Could not extract rules" in result.output
        assert "preserved" in result.output
        # Original file should be preserved (not archived, not deleted)
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "snake_case" in content  # User's original content still there
        monkeypatch.undo()

    def test_init_archives_cursorrules(self, tmp_path: Path) -> None:
        """vibe init should archive .cursorrules."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / ".cursorrules").write_text("- Use semicolons\n")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        archived = tmp_path / ".vibe" / "archive" / "legacy" / ".cursorrules"
        assert archived.exists()
        assert not (tmp_path / ".cursorrules").exists()
        monkeypatch.undo()

    def test_init_zh_tw(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["init", "--lang", "zh-TW"])
        assert result.exit_code == 0
        # VIBE.md no longer generated; check state files instead
        tasks = (tmp_path / ".vibe" / "state" / "tasks.md").read_text(encoding="utf-8")
        assert "任務" in tasks or "Tasks" in tasks  # zh-TW or fallback
        monkeypatch.undo()

    def test_init_force_preserves_existing_lang(self, tmp_path: Path) -> None:
        """`vibe init --force` without --lang should keep the previously chosen lang."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        # Initial init in zh-TW
        runner.invoke(app, ["init", "--lang", "zh-TW"])
        config_before = load_config(tmp_path / ".vibe")
        assert config_before.vibe.lang == "zh-TW"
        # Force reinit without --lang should preserve zh-TW
        result = runner.invoke(app, ["init", "--force"])
        assert result.exit_code == 0
        config_after = load_config(tmp_path / ".vibe")
        assert config_after.vibe.lang == "zh-TW"
        mp.undo()

    def test_init_force_explicit_lang_overrides(self, tmp_path: Path) -> None:
        """`vibe init --force --lang en` should override existing zh-TW."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init", "--lang", "zh-TW"])
        result = runner.invoke(app, ["init", "--force", "--lang", "en"])
        assert result.exit_code == 0
        assert load_config(tmp_path / ".vibe").vibe.lang == "en"
        mp.undo()

    def test_init_invalid_lang_fallback(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["init", "--lang", "xx"])
        assert "not a supported language" in result.output
        assert result.exit_code == 0  # Falls back to en
        monkeypatch.undo()


# ── Status scenarios ──


class TestCliVersion:
    def test_version_flag_long(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "vibe-state-cli" in result.output
        # Match the canonical version pattern (e.g. "vibe-state-cli 0.3.4")
        assert any(ch.isdigit() for ch in result.output)

    def test_version_flag_short(self) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "vibe-state-cli" in result.output


class TestCliStatus:
    def test_status_without_init(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "vibe init" in result.output
        monkeypatch.undo()

    def test_status_never_synced_shows_never(self, tmp_path: Path) -> None:
        """Fresh init, no sync yet — should show 'never synced'."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "never synced" in result.output
        # Health should be FRESH (just inited, < 3 days)
        assert "FRESH" in result.output
        mp.undo()

    def test_status_shows_fresh_when_just_synced(self, tmp_path: Path) -> None:
        """After sync with no new commits, should show 'state is current' + FRESH."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        # Need at least one commit for git to have a HEAD
        (tmp_path / "README.md").write_text("hi\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True
        )
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        runner.invoke(app, ["sync"])
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "state is current" in result.output
        assert "FRESH" in result.output
        mp.undo()

    def test_status_shows_commits_behind(self, tmp_path: Path) -> None:
        """After sync, new commits should appear as 'N commits behind'."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("hi\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True
        )
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        runner.invoke(app, ["sync"])
        # Add 3 new commits after sync
        for i in range(3):
            (tmp_path / f"f{i}.txt").write_text(str(i))
            subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"feat {i}"], cwd=tmp_path, capture_output=True
            )
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "3 commits behind" in result.output
        mp.undo()

    def test_status_zh_tw_locale(self, tmp_path: Path) -> None:
        """When config.vibe.lang = zh-TW, status output should be Chinese."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init", "--lang", "zh-TW"])
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "生命週期" in result.output
        assert "上次同步" in result.output
        assert "狀態健康度" in result.output
        # Should NOT contain English labels
        assert "Lifecycle" not in result.output
        mp.undo()

    def test_status_adapter_missing(self, tmp_path: Path) -> None:
        """Deleting an adapter file should show 'missing' in status."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        # Delete AGENTS.md (default adapter)
        (tmp_path / "AGENTS.md").unlink()
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "missing" in result.output
        mp.undo()


# ── Start scenarios ──


class TestCliStart:
    def test_start_auto_compact_triggered(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        big = "# Tasks\n" + "".join(f"- [ ] Task {i}\n" for i in range(200))
        write_state_file(tmp_path / ".vibe", "tasks.md", big)
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0
        assert "Auto-compacting" in result.output
        mp.undo()

    def test_start_auto_syncs_new_commits(self, tmp_path: Path) -> None:
        """Start should pull new commits into state without requiring manual sync."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("hi\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True
        )
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])  # First start syncs the init commit
        # Add 2 new commits without running sync
        for i in range(2):
            (tmp_path / f"f{i}.txt").write_text(str(i))
            subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"feat {i}"], cwd=tmp_path, capture_output=True
            )
        # Second start should auto-sync those 2 commits
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0
        assert "Auto-synced" in result.output
        assert "2 new commits" in result.output
        mp.undo()

    def test_start_with_experiments(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        write_state_file(
            tmp_path / ".vibe", "experiments.md",
            "# Exp\n- [KEPT] abc\n- [REVERTED] def\n",
        )
        result = runner.invoke(app, ["start"])
        assert "1 kept" in result.output
        mp.undo()

    def test_start_with_open_issues(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        write_state_file(
            tmp_path / ".vibe", "current.md",
            "# Current\n## Open Issues\n- Bug #42\n- Bug #99\n",
        )
        result = runner.invoke(app, ["start"])
        assert "Bug" in result.output
        mp.undo()

    def test_start_with_pending_tasks(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        write_state_file(
            tmp_path / ".vibe", "tasks.md",
            "# Tasks\n- [ ] Build auth\n- [ ] Write tests\n",
        )
        result = runner.invoke(app, ["start"])
        assert "Build auth" in result.output
        mp.undo()

    def test_start_no_git(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["start"])
        assert "disabled" in result.output
        mp.undo()

    def test_start_git_not_in_path(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        with patch("vibe_state.core.git_ops.git_available", return_value=False):
            result = runner.invoke(app, ["start"])
        assert "git not found" in result.output
        mp.undo()


# ── Sync scenarios ──


class TestCliSync:
    def test_sync_non_git(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        result = runner.invoke(app, ["sync"])
        assert "No git" in result.output or "No changes" in result.output
        mp.undo()

    def test_sync_many_commits(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("init")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=tmp_path, capture_output=True,
        )
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        for i in range(25):
            (tmp_path / "f.txt").write_text(f"v{i}")
            subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", f"feat: change {i}"],
                cwd=tmp_path, capture_output=True,
            )
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        current = read_state_file(tmp_path / ".vibe", "current.md")
        assert "... and" in current  # Truncated at 20
        mp.undo()

    def test_sync_note_appends_to_progress_summary(self, tmp_path: Path) -> None:
        """sync --note should write a dated semantic note inside Progress Summary."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        result = runner.invoke(
            app, ["sync", "--note", "three-tier adapter refactor for token efficiency"]
        )
        assert result.exit_code == 0
        assert "Note added" in result.output
        current = read_state_file(tmp_path / ".vibe", "current.md")
        assert "three-tier adapter refactor for token efficiency" in current
        # Note should sit inside Progress Summary, before Open Issues
        progress_idx = current.find("Progress Summary")
        note_idx = current.find("three-tier adapter")
        issues_idx = current.find("Open Issues")
        assert progress_idx < note_idx
        if issues_idx > 0:
            assert note_idx < issues_idx
        mp.undo()

    def test_sync_note_zh_tw_section(self, tmp_path: Path) -> None:
        """sync --note should also recognize zh-TW heading 進度摘要."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init", "--lang", "zh-TW"])
        runner.invoke(app, ["start"])
        result = runner.invoke(app, ["sync", "--note", "三層 adapter 重構"])
        assert result.exit_code == 0
        current = read_state_file(tmp_path / ".vibe", "current.md")
        assert "三層 adapter 重構" in current
        progress_idx = current.find("進度摘要")
        note_idx = current.find("三層 adapter")
        assert progress_idx >= 0
        assert progress_idx < note_idx
        mp.undo()

    def test_sync_no_refresh_suppresses_clear_checklist(self, tmp_path: Path) -> None:
        """sync --no-refresh should not print C.L.E.A.R. checklist (used by hook).

        The hook redirects sync output to .hook.log; the checklist is for
        humans, so leaking it into the log file is noise.
        """
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("init")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=tmp_path, capture_output=True,
        )
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        (tmp_path / "f.txt").write_text("v2")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: change"],
            cwd=tmp_path, capture_output=True,
        )
        result = runner.invoke(app, ["sync", "--no-refresh"])
        assert result.exit_code == 0
        # Plain sync should print the checklist; --no-refresh should not.
        assert "C.L.E.A.R" not in result.output
        assert "Core Logic" not in result.output
        mp.undo()

    def test_sync_no_refresh_skips_adapter_update(self, tmp_path: Path) -> None:
        """sync --no-refresh should not modify adapter files (used by git hook)."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("init")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=tmp_path, capture_output=True,
        )
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        agents_md = tmp_path / "AGENTS.md"
        before_mtime = agents_md.stat().st_mtime
        # Add a new commit
        (tmp_path / "f.txt").write_text("v2")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: change"],
            cwd=tmp_path, capture_output=True,
        )
        result = runner.invoke(app, ["sync", "--no-refresh"])
        assert result.exit_code == 0
        # AGENTS.md should NOT have been touched
        assert agents_md.stat().st_mtime == before_mtime
        # State file should still be updated
        current = read_state_file(tmp_path / ".vibe", "current.md")
        assert "feat: change" in current
        mp.undo()

    def test_sync_includes_diff_stat(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "app.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=tmp_path, capture_output=True,
        )
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        (tmp_path / "new_feature.py").write_text("print('hello')\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: add new feature"],
            cwd=tmp_path, capture_output=True,
        )
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        current = read_state_file(tmp_path / ".vibe", "current.md")
        assert "Files changed" in current
        assert "new_feature.py" in current
        mp.undo()

    def test_sync_records_experiments(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=tmp_path, capture_output=True,
        )
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        (tmp_path / "exp.txt").write_text("1")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "autoresearch: try A"],
            cwd=tmp_path, capture_output=True,
        )
        (tmp_path / "exp.txt").write_text("2")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "autoresearch: revert B"],
            cwd=tmp_path, capture_output=True,
        )
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        exp = read_state_file(tmp_path / ".vibe", "experiments.md")
        assert "[KEPT]" in exp or "[REVERTED]" in exp
        mp.undo()


# ── Adapt scenarios ──


class TestCliAdapt:
    def test_adapt_list(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        result = runner.invoke(app, ["adapt", "--list"])
        assert result.exit_code == 0
        assert "agents_md" in result.output
        result = runner.invoke(app, ["adapt", "--add", "claude"])
        assert result.exit_code == 0
        result = runner.invoke(app, ["adapt", "--list"])
        assert "claude" in result.output
        result = runner.invoke(app, ["adapt", "--add", "fake_tool"])
        assert result.exit_code == 1
        monkeypatch.undo()

    def test_add_duplicate(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["adapt", "--add", "agents_md"])
        assert "already enabled" in result.output
        mp.undo()

    def test_add_invalid(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["adapt", "--add", "nonexistent"])
        assert result.exit_code == 1
        assert "Unknown adapter" in result.output
        monkeypatch.undo()

    def test_remove_not_enabled(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["adapt", "--remove", "cursor"])
        assert "not enabled" in result.output
        mp.undo()

    def test_remove_without_confirm_shows_warning(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        runner.invoke(app, ["adapt", "--add", "claude"])
        runner.invoke(app, ["adapt", "--sync", "--confirm"])
        result = runner.invoke(app, ["adapt", "--remove", "claude"])
        assert "--confirm" in result.output
        mp.undo()

    def test_remove_dry_run(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        runner.invoke(app, ["adapt", "--add", "claude"])
        runner.invoke(app, ["adapt", "--sync", "--confirm"])
        result = runner.invoke(app, ["adapt", "--remove", "claude", "--dry-run"])
        assert "dry-run" in result.output
        assert (tmp_path / "CLAUDE.md").exists()
        monkeypatch.undo()

    def test_remove_confirm(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        runner.invoke(app, ["adapt", "--add", "claude"])
        runner.invoke(app, ["adapt", "--sync", "--confirm"])
        result = runner.invoke(app, ["adapt", "--remove", "claude", "--confirm"])
        assert result.exit_code == 0
        backup_dir = tmp_path / ".vibe" / "backups" / "claude"
        assert backup_dir.exists()
        monkeypatch.undo()

    def test_remove_unknown_in_config(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        config = load_config(tmp_path / ".vibe")
        config.adapters.enabled.append("fake_adapter")
        save_config(tmp_path / ".vibe", config)
        result = runner.invoke(app, ["adapt", "--remove", "fake_adapter", "--confirm"])
        assert "Unknown adapter" in result.output
        mp.undo()

    def test_sync_regenerates(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        runner.invoke(app, ["adapt", "--add", "cursor"])
        result = runner.invoke(app, ["adapt", "--sync", "--confirm"])
        assert "synced" in result.output
        assert (tmp_path / ".cursor" / "rules" / "vibe-standards.mdc").exists()
        monkeypatch.undo()

    def test_sync_with_unknown_adapter(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        config = load_config(tmp_path / ".vibe")
        config.adapters.enabled.append("nonexistent")
        save_config(tmp_path / ".vibe", config)
        result = runner.invoke(app, ["adapt", "--sync", "--confirm"])
        assert "Unknown adapter" in result.output
        mp.undo()

    def test_no_flag_shows_help(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["adapt"])
        assert "--add" in result.output or "--remove" in result.output or "--list" in result.output
        mp.undo()


# ── Integrity marker ──


class TestCliIntegrity:
    def test_adapter_files_have_managed_marker(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "<!-- vibe-state-cli:managed -->" in agents_md
        monkeypatch.undo()

    def test_json_files_no_marker(self, tmp_path: Path) -> None:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / ".claude").mkdir()
        runner.invoke(app, ["init"])
        settings = tmp_path / ".claude" / "settings.json"
        if settings.exists():
            import json

            content = settings.read_text(encoding="utf-8")
            assert "<!-- vibe-state-cli" not in content
            json.loads(content)
        monkeypatch.undo()


# ── Extract progress ──


class TestCliExtractProgress:
    def test_finds_last_sync_block(self) -> None:
        content = (
            "# Current\n## Progress\nOld stuff\n"
            "## Sync [2026-04-07 10:00]\nCommits: 3 since last sync\n"
            "## Sync [2026-04-07 14:00]\nCommits: 5 since last sync\n"
        )
        result = extract_latest_progress(content)
        assert "14:00" in result
        assert "5" in result

    def test_finds_final_sync(self) -> None:
        content = "# Current\n## Final Sync [2026-04-07]\nDone\n"
        result = extract_latest_progress(content)
        assert "Final Sync" in result

    def test_sync_header_only(self) -> None:
        content = "# Current\n## Sync [2026-04-07]\n```\ncode\n```\n"
        result = extract_latest_progress(content)
        assert "2026-04-07" in result
        assert "code" in result

    def test_fallback_to_progress_section(self) -> None:
        content = "# Current\n## Progress Summary\nProject is 50% done\n"
        result = extract_latest_progress(content)
        assert "50%" in result

    def test_empty_returns_default(self) -> None:
        assert "no progress" in extract_latest_progress("")

    def test_no_matching_section(self) -> None:
        content = "# Current\nJust some text\n"
        result = extract_latest_progress(content)
        assert "no progress" in result

    def test_returns_header_when_only_code_follows(self) -> None:
        content = "## Sync [2026-04-08]\n```\n```\n```\n```\n"
        result = extract_latest_progress(content)
        assert result == "## Sync [2026-04-08]"

    def test_sync_header_followed_only_by_code_blocks(self) -> None:
        content = "# Current\n## Sync [2026-04-07]\n```\nabc1234 feat: add auth\n```\n"
        result = extract_latest_progress(content)
        assert "2026-04-07" in result
        assert "feat: add auth" in result


# ── Extract section items ──


class TestCliExtractSectionItems:
    def test_extracts_items(self) -> None:
        content = "## Open Issues\n- Bug #1\n- Bug #2\n## Other\n"
        items = extract_section_items(content, "Open Issues")
        assert items == ["- Bug #1", "- Bug #2"]

    def test_skips_none_marker(self) -> None:
        content = "## Open Issues\n- (none)\n"
        items = extract_section_items(content, "Open Issues")
        assert items == []

    def test_stops_at_next_section(self) -> None:
        content = "## Open Issues\n- Bug\n## Tasks\n- Task\n"
        items = extract_section_items(content, "Open Issues")
        assert len(items) == 1

    def test_missing_section(self) -> None:
        items = extract_section_items("# Nothing here\n", "Open Issues")
        assert items == []


class TestCliVerboseMode:
    def test_verbose_flag_accepted(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["--verbose", "init"])
        assert result.exit_code == 0
        mp.undo()

    def test_verbose_short_flag(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["-v", "init"])
        assert result.exit_code == 0
        mp.undo()

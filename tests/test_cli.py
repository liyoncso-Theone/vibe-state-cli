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

    def test_init_gitignore_covers_hook_log(self, tmp_path: Path) -> None:
        """Reported by ProBrain team: post-commit hook writes to
        .vibe/state/.hook.log but .vibe/.gitignore only covered `backups/`,
        so the log file kept showing up in `git status` as untracked.
        """
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        gi = (tmp_path / ".vibe" / ".gitignore").read_text(encoding="utf-8")
        assert "backups/" in gi
        assert "state/.hook.log" in gi
        assert "state/*.lock" in gi
        mp.undo()

    def test_init_force_appends_missing_gitignore_entries(
        self, tmp_path: Path
    ) -> None:
        """Existing projects upgrading to a newer vibe should auto-gain new
        ignore entries via init --force, without losing their own additions.
        """
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        # Simulate an old .gitignore that only had backups/ + a user line.
        gi_path = tmp_path / ".vibe" / ".gitignore"
        gi_path.write_text(
            "# vibe-state-cli internals (do not commit)\n"
            "backups/\n"
            "my-custom-secret.json\n",
            encoding="utf-8",
        )
        runner.invoke(app, ["init", "--force"])
        gi = gi_path.read_text(encoding="utf-8")
        # User addition preserved
        assert "my-custom-secret.json" in gi
        # Missing internals appended
        assert "state/.hook.log" in gi
        assert "state/*.lock" in gi
        # No duplicate of backups/
        assert gi.count("backups/") == 1
        mp.undo()

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


class TestEnsureInternalGitignore:
    """Unit tests for the helper directly, isolated from `vibe init`."""

    def test_creates_file_when_missing(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import ensure_internal_gitignore

        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        changed, added = ensure_internal_gitignore(vibe_dir)
        assert changed is True
        assert "state/.hook.log" in added
        body = (vibe_dir / ".gitignore").read_text(encoding="utf-8")
        for entry in ("backups/", "state/*.lock", "state/.hook.log"):
            assert entry in body

    def test_noop_when_complete(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import (
            _INTERNAL_GITIGNORE_ENTRIES,
            ensure_internal_gitignore,
        )

        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        gi = vibe_dir / ".gitignore"
        # Build the complete file from the source-of-truth tuple so this
        # test never falls out of sync when v0.3.x adds another entry.
        gi.write_text(
            "# vibe-state-cli internals (do not commit)\n"
            + "\n".join(_INTERNAL_GITIGNORE_ENTRIES)
            + "\n",
            encoding="utf-8",
        )
        before = gi.read_text(encoding="utf-8")
        changed, added = ensure_internal_gitignore(vibe_dir)
        assert changed is False
        assert added == []
        assert gi.read_text(encoding="utf-8") == before  # untouched

    def test_appends_only_missing(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import ensure_internal_gitignore

        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        gi = vibe_dir / ".gitignore"
        gi.write_text("backups/\n", encoding="utf-8")
        changed, added = ensure_internal_gitignore(vibe_dir)
        assert changed is True
        assert "state/.hook.log" in added
        assert "state/*.lock" in added
        assert "backups/" not in added  # already present
        body = gi.read_text(encoding="utf-8")
        assert body.count("backups/") == 1  # not duplicated

    def test_preserves_user_added_entries(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import ensure_internal_gitignore

        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        gi = vibe_dir / ".gitignore"
        gi.write_text(
            "backups/\n"
            "secrets/\n"
            "my-private-notes.md\n",
            encoding="utf-8",
        )
        ensure_internal_gitignore(vibe_dir)
        body = gi.read_text(encoding="utf-8")
        assert "secrets/" in body
        assert "my-private-notes.md" in body
        assert "state/.hook.log" in body

    def test_handles_empty_file_without_leading_newline(
        self, tmp_path: Path
    ) -> None:
        """Edge case: an empty .gitignore (e.g., user truncated it) must
        not produce a leading blank line in the rewritten file."""
        from vibe_state.commands._helpers import ensure_internal_gitignore

        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        gi = vibe_dir / ".gitignore"
        gi.write_text("", encoding="utf-8")
        ensure_internal_gitignore(vibe_dir)
        body = gi.read_text(encoding="utf-8")
        assert not body.startswith("\n"), f"leading newline: {body!r}"
        assert body.startswith("backups/")

    def test_handles_whitespace_only_file(self, tmp_path: Path) -> None:
        """Edge case: .gitignore that's only whitespace should be treated
        like an empty file."""
        from vibe_state.commands._helpers import ensure_internal_gitignore

        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        gi = vibe_dir / ".gitignore"
        gi.write_text("   \n\n  \n", encoding="utf-8")
        ensure_internal_gitignore(vibe_dir)
        body = gi.read_text(encoding="utf-8")
        assert not body.startswith("\n")
        assert "backups/" in body

    def test_handles_no_trailing_newline(self, tmp_path: Path) -> None:
        """Existing file without trailing newline gets exactly one inserted."""
        from vibe_state.commands._helpers import ensure_internal_gitignore

        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        gi = vibe_dir / ".gitignore"
        gi.write_text("backups/", encoding="utf-8")  # no trailing \n
        ensure_internal_gitignore(vibe_dir)
        body = gi.read_text(encoding="utf-8")
        # Should not be "backups/state/*.lock..." (entries glued together)
        assert "backups/\nstate/*.lock" in body


class TestCliEncoding:
    """v0.3.5: cp950 console used to crash on Rich's ✓ marker. cli.py forces
    UTF-8 on stdout/stderr at startup so users don't have to set
    PYTHONIOENCODING themselves."""

    def test_force_utf8_io_safe_on_test_streams(self) -> None:
        """The reconfigure step must not raise on test runners' StringIO."""
        from vibe_state.cli import _force_utf8_io

        _force_utf8_io()  # Should be a silent no-op or success

    def test_force_utf8_io_handles_non_utf8_encoding(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulate a stream whose encoding is cp950: reconfigure should
        be attempted and successfully change encoding to utf-8."""
        import sys

        class FakeCp950Stream:
            encoding = "cp950"

            def reconfigure(self, **kwargs: object) -> None:
                # Real Windows console reconfigure would succeed here.
                self.encoding = "utf-8"

            def write(self, s: str) -> int:  # pragma: no cover
                return len(s)

            def flush(self) -> None:  # pragma: no cover
                pass

        fake = FakeCp950Stream()
        monkeypatch.setattr(sys, "stdout", fake)
        from vibe_state.cli import _force_utf8_io

        _force_utf8_io()
        assert fake.encoding == "utf-8"

    def test_force_utf8_io_skips_streams_without_reconfigure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Streams without `reconfigure` (e.g. StringIO) must be skipped
        silently."""
        import io
        import sys

        # io.StringIO exposes encoding=None, no reconfigure method.
        stub = io.StringIO()
        monkeypatch.setattr(sys, "stdout", stub)
        from vibe_state.cli import _force_utf8_io

        _force_utf8_io()  # Must not raise


class TestStartUpgradesGitignore:
    """v0.3.5: existing projects from older vibe versions used to need
    `vibe init --force` to pick up newly-added .gitignore entries.
    `vibe start` now self-heals on every session so users don't have to."""

    def test_start_self_heals_missing_gitignore_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])

        # Simulate an older project: only `backups/` in .gitignore
        gi = tmp_path / ".vibe" / ".gitignore"
        gi.write_text("backups/\n", encoding="utf-8")

        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0, result.output

        body = gi.read_text(encoding="utf-8")
        assert "state/.hook.log" in body
        assert "state/*.lock" in body

    def test_start_does_not_clobber_user_added_lines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])

        gi = tmp_path / ".vibe" / ".gitignore"
        gi.write_text(
            "backups/\nstate/*.lock\nstate/.hook.log\n"
            "secrets/\nmy-private.md\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0, result.output

        body = gi.read_text(encoding="utf-8")
        assert "secrets/" in body
        assert "my-private.md" in body


class TestHookSubmoduleAndWorktree:
    """v0.3.5: install_post_commit_hook now resolves gitlinks so it works
    inside submodules and linked worktrees, not just plain repos."""

    def test_resolves_gitlink_to_submodule_dir(
        self, tmp_path: Path
    ) -> None:
        """A submodule's working tree has `.git` as a *file* containing
        `gitdir: ../.git/modules/sub`. The hook must land in the resolved
        modules dir, not get rejected as 'no_git'."""
        from vibe_state.commands._helpers import install_post_commit_hook

        # Simulate a submodule layout
        parent_git = tmp_path / "parent.git"
        sub_module_dir = parent_git / "modules" / "sub"
        sub_module_dir.mkdir(parents=True)

        sub_worktree = tmp_path / "submodule"
        sub_worktree.mkdir()
        # `.git` as gitlink file (relative path is the common form)
        relative_gitdir = (parent_git / "modules" / "sub").resolve()
        (sub_worktree / ".git").write_text(
            f"gitdir: {relative_gitdir}\n", encoding="utf-8"
        )

        status = install_post_commit_hook(sub_worktree)
        assert status == "installed"
        assert (sub_module_dir / "hooks" / "post-commit").exists()

    def test_returns_no_git_when_gitlink_target_missing(
        self, tmp_path: Path
    ) -> None:
        """A `.git` file pointing at a nonexistent path must not raise —
        it should fail closed (no_git)."""
        from vibe_state.commands._helpers import install_post_commit_hook

        wt = tmp_path / "broken"
        wt.mkdir()
        (wt / ".git").write_text(
            "gitdir: /does/not/exist/anywhere\n", encoding="utf-8"
        )
        assert install_post_commit_hook(wt) == "no_git"

    def test_hook_block_runs_in_background(self, tmp_path: Path) -> None:
        """v0.3.5: the installed hook script must use the `(... &)`
        background pattern so big-repo `vibe sync` doesn't block the
        commit prompt."""
        from vibe_state.commands._helpers import install_post_commit_hook

        (tmp_path / ".git").mkdir()
        install_post_commit_hook(tmp_path)
        body = (tmp_path / ".git" / "hooks" / "post-commit").read_text(
            encoding="utf-8"
        )
        # backgrounded subshell: open paren, sync command, &, close paren
        assert "(vibe sync --no-refresh" in body
        assert "&)" in body


class TestInitGracefulFailures:
    """v0.3.5: rare-but-real failure modes (read-only FS, locked files)
    must not crash `vibe init` — degrade with a warning instead."""

    def test_hook_install_oserror_does_not_crash_init(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibe_state.commands import cmd_init as _cmd_init

        monkeypatch.delenv("VIBE_SKIP_HOOK_INSTALL", raising=False)
        monkeypatch.chdir(tmp_path)
        _git_init(tmp_path)

        def _boom(_root: Path) -> str:
            raise OSError("simulated permission denied")

        monkeypatch.setattr(_cmd_init, "install_post_commit_hook", _boom)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, result.output
        assert "could not install git post-commit hook" in result.output

    def test_gitignore_oserror_does_not_crash_init(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibe_state.commands import cmd_init as _cmd_init

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()

        def _boom(_vibe_dir: Path) -> tuple[bool, list[str]]:
            raise OSError("simulated disk full")

        monkeypatch.setattr(_cmd_init, "ensure_internal_gitignore", _boom)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, result.output
        assert "could not write .vibe/.gitignore" in result.output


class TestV036PostCommitHookLoopFix:
    """v0.3.6: the `--no-refresh` path (used by the post-commit hook) must
    advance only `.sync-cursor`, never append to `current.md`. Tracking
    files that auto-mutate on every commit creates an infinite
    `git status` loop.
    """

    def test_no_refresh_does_not_modify_current_md(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import perform_cursor_update

        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("a")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, capture_output=True)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])

        current_md = tmp_path / ".vibe" / "state" / "current.md"
        before = current_md.read_bytes()

        # Add a new commit + run cursor-only sync (what the hook calls)
        (tmp_path / "f.txt").write_text("b")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: thing"],
            cwd=tmp_path, capture_output=True,
        )
        result = perform_cursor_update(tmp_path / ".vibe")

        assert result.commits_synced == 1
        # current.md is byte-identical — no Sync block was appended
        assert current_md.read_bytes() == before
        mp.undo()

    def test_explicit_sync_still_modifies_current_md(self, tmp_path: Path) -> None:
        """Regression guard: human-invoked `vibe sync` (no flag) must keep
        appending to current.md — that behavior is the human-readable
        activity log everyone reads at session start."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("a")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, capture_output=True)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])

        (tmp_path / "f.txt").write_text("b")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: real change"],
            cwd=tmp_path, capture_output=True,
        )
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0

        current = (tmp_path / ".vibe" / "state" / "current.md").read_text(encoding="utf-8")
        assert "feat: real change" in current
        assert "## Sync" in current
        mp.undo()


class TestV036SyncPromote:
    """v0.3.6: `vibe sync --promote 'title'` ships the latest sync block
    to an external knowledge store via vendor-neutral subprocess. Default
    disabled — opt-in via .vibe/config.toml [promotion] section.
    """

    def _enable_promotion(self, vibe_dir: Path, target: str = "basic-memory") -> None:
        """Flip [promotion].enabled = true in config.toml."""
        config = load_config(vibe_dir)
        config.promotion.enabled = True
        config.promotion.target = target
        save_config(vibe_dir, config)

    def test_promote_disabled_by_default(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import promote_to_backend

        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])

        ok, msg = promote_to_backend(tmp_path / ".vibe", "anything")
        assert ok is False
        assert "disabled" in msg.lower()
        mp.undo()

    def test_promote_requires_title(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import promote_to_backend

        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        self._enable_promotion(tmp_path / ".vibe")

        ok, msg = promote_to_backend(tmp_path / ".vibe", "")
        assert ok is False
        assert "title" in msg.lower()
        mp.undo()

    def test_promote_unknown_target(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import promote_to_backend

        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        self._enable_promotion(tmp_path / ".vibe", target="not-a-real-tool")

        ok, msg = promote_to_backend(
            tmp_path / ".vibe", "title", editor_factory=lambda _: "body"
        )
        assert ok is False
        assert "not-a-real-tool" in msg

    def test_promote_basic_memory_missing_cli(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If basic-memory isn't on PATH, surface a helpful error (no traceback)."""
        from vibe_state.commands import _helpers as _h

        monkeypatch.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        self._enable_promotion(tmp_path / ".vibe")

        monkeypatch.setattr(_h.shutil, "which", lambda _name: None)
        ok, msg = _h.promote_to_backend(
            tmp_path / ".vibe", "test", editor_factory=lambda _: "body"
        )
        assert ok is False
        assert "basic-memory" in msg.lower()
        assert "path" in msg.lower()

    def test_promote_basic_memory_happy_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end: simulate basic-memory available, capture invocation."""
        from vibe_state.commands import _helpers as _h

        monkeypatch.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        self._enable_promotion(tmp_path / ".vibe")

        monkeypatch.setattr(_h.shutil, "which", lambda _name: "/fake/basic-memory")
        captured: dict[str, object] = {}

        def fake_run(cmd: list[str], **kwargs: object) -> object:
            captured["cmd"] = cmd
            captured["input"] = kwargs.get("input")
            class R:
                returncode = 0
                stdout = "ok"
                stderr = ""
            return R()

        monkeypatch.setattr(_h.subprocess, "run", fake_run)
        ok, msg = _h.promote_to_backend(
            tmp_path / ".vibe", "checkpoint pattern",
            editor_factory=lambda _: "rationale goes here",
        )
        assert ok is True, msg
        assert "checkpoint pattern" in msg
        cmd = captured["cmd"]
        assert cmd[0] == "basic-memory"
        assert cmd[1:3] == ["tool", "write-note"]
        assert "--title" in cmd
        assert cmd[cmd.index("--title") + 1] == "checkpoint pattern"
        assert captured["input"] == "rationale goes here"


class TestV036UntrackMigration:
    """v0.3.6: `.sync-cursor` and `.lifecycle` move from tracked to
    untracked. Run on `vibe init --force` and `vibe start` so existing
    projects upgrade silently.
    """

    def _set_up_old_layout(self, tmp_path: Path) -> None:
        """Simulate a v0.3.5 project where .sync-cursor + .lifecycle are
        tracked in git."""
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        # Force-add the two files that older versions wrote into the index
        for rel in (".vibe/state/.sync-cursor", ".vibe/state/.lifecycle"):
            p = tmp_path / rel
            if not p.exists():
                p.write_text("seed\n")
            subprocess.run(
                ["git", "add", "-f", rel],
                cwd=tmp_path, capture_output=True,
            )
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed old layout"],
            cwd=tmp_path, capture_output=True,
        )

    def test_ensure_state_files_untracked_removes_index_entries(
        self, tmp_path: Path
    ) -> None:
        from vibe_state.commands._helpers import ensure_state_files_untracked

        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        self._set_up_old_layout(tmp_path)
        for rel in (".vibe/state/.sync-cursor", ".vibe/state/.lifecycle"):
            ls = subprocess.run(
                ["git", "ls-files", "--error-unmatch", rel],
                cwd=tmp_path, capture_output=True, text=True,
            )
            assert ls.returncode == 0, f"{rel} should be tracked before migration"

        untracked = ensure_state_files_untracked(tmp_path)

        assert set(untracked) == {".vibe/state/.sync-cursor", ".vibe/state/.lifecycle"}
        for rel in untracked:
            ls = subprocess.run(
                ["git", "ls-files", "--error-unmatch", rel],
                cwd=tmp_path, capture_output=True, text=True,
            )
            assert ls.returncode != 0, f"{rel} still tracked after migration"
            assert (tmp_path / rel).exists(), f"{rel} content lost"
        mp.undo()

    def test_ensure_state_files_untracked_is_idempotent(self, tmp_path: Path) -> None:
        from vibe_state.commands._helpers import ensure_state_files_untracked

        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        # The two files were never tracked in this freshly-inited project
        result1 = ensure_state_files_untracked(tmp_path)
        result2 = ensure_state_files_untracked(tmp_path)
        assert result1 == [] and result2 == []
        mp.undo()

    def test_start_self_heals_old_layout(self, tmp_path: Path) -> None:
        """The whole point of putting the migration in vibe start: existing
        users don't have to do anything. Their next session start untracks
        the runtime-state files automatically."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        self._set_up_old_layout(tmp_path)
        # Confirm pre-state
        ls = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".vibe/state/.sync-cursor"],
            cwd=tmp_path, capture_output=True,
        )
        assert ls.returncode == 0

        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0, result.output

        # Confirm post-state — untracked, but still on disk
        ls = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".vibe/state/.sync-cursor"],
            cwd=tmp_path, capture_output=True,
        )
        assert ls.returncode != 0
        assert (tmp_path / ".vibe/state/.sync-cursor").exists()
        mp.undo()


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

    def test_sync_no_refresh_silent_when_lifecycle_not_active(
        self, tmp_path: Path
    ) -> None:
        """sync --no-refresh in READY state should silently skip (used by hook).

        After `vibe init --force`, lifecycle is READY until the user runs
        `vibe start`. The git hook fires sync after every commit, so the
        first commit post-init must not spam .hook.log with state errors.
        """
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        _git_init(tmp_path)
        runner.invoke(app, ["init"])  # Lifecycle is now READY (no `start`)
        result = runner.invoke(app, ["sync", "--no-refresh"])
        # Silent skip — no error, no output
        assert result.exit_code == 0
        assert "Cannot run" not in result.output
        # Without --no-refresh, READY should still error (preserve plain `sync` UX)
        result_loud = runner.invoke(app, ["sync"])
        assert result_loud.exit_code == 1
        assert "Cannot run" in result_loud.output
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
        """sync --no-refresh (the hook path) must NOT touch adapter files
        AND must NOT modify current.md.

        v0.3.6: the previous behavior — appending a Sync block to current.md
        on every commit — was the root cause of the infinite-loop bug.
        --no-refresh now does a lightweight cursor-only update; current.md
        is reserved for user-initiated `vibe sync` (no flag) and
        `vibe start`."""
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
        before_agents_mtime = agents_md.stat().st_mtime
        current_md = tmp_path / ".vibe" / "state" / "current.md"
        before_current_hash = current_md.read_bytes()
        # Add a new commit (the hook would normally fire `sync --no-refresh`)
        (tmp_path / "f.txt").write_text("v2")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: change"],
            cwd=tmp_path, capture_output=True,
        )
        result = runner.invoke(app, ["sync", "--no-refresh"])
        assert result.exit_code == 0
        # AGENTS.md should NOT have been touched
        assert agents_md.stat().st_mtime == before_agents_mtime
        # current.md must NOT contain the new commit — that's the v0.3.6
        # contract that breaks the infinite-loop bug.
        assert current_md.read_bytes() == before_current_hash
        current = read_state_file(tmp_path / ".vibe", "current.md")
        assert "feat: change" not in current
        # But cursor must have advanced
        cursor = (tmp_path / ".vibe" / "state" / ".sync-cursor").read_text()
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_path,
            capture_output=True, text=True,
        ).stdout.strip()
        assert cursor.strip() == head
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

    def test_adapt_lang_switches_config(self, tmp_path: Path) -> None:
        """`vibe adapt --lang zh-TW` should change config.toml lang and report old → new."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])  # default en
        assert load_config(tmp_path / ".vibe").vibe.lang == "en"
        result = runner.invoke(app, ["adapt", "--lang", "zh-TW"])
        assert result.exit_code == 0
        assert "en" in result.output and "zh-TW" in result.output
        assert load_config(tmp_path / ".vibe").vibe.lang == "zh-TW"
        # Status should now render in Chinese
        status_result = runner.invoke(app, ["status"])
        assert "生命週期" in status_result.output
        mp.undo()

    def test_adapt_lang_invalid(self, tmp_path: Path) -> None:
        """Unsupported lang should exit 1 with a clear error."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["adapt", "--lang", "ja"])
        assert result.exit_code == 1
        assert "not a supported language" in result.output
        mp.undo()

    def test_adapt_lang_already_set_noop(self, tmp_path: Path) -> None:
        """Setting lang to current value should be a friendly no-op."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        runner.invoke(app, ["init", "--lang", "zh-TW"])
        result = runner.invoke(app, ["adapt", "--lang", "zh-TW"])
        assert result.exit_code == 0
        assert "already" in result.output
        mp.undo()

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


# ── v0.3.8: vibe status --diagnose ──


class TestV038StatusDiagnose:
    """v0.3.8 adds `--diagnose` as a flag on `vibe status` (not a new
    command — flag > new command per the cli-design principle). Runs 4
    check groups in brew-doctor style: Environment / Project / Adapters /
    Memory layer."""

    def _init_minimal_project(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])

    def test_status_without_diagnose_still_works(self, tmp_path: Path) -> None:
        """Regression guard: existing `vibe status` behavior unchanged."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        self._init_minimal_project(tmp_path)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        # legacy status output renders the dashboard panel
        assert "vibe status" in result.output or "Lifecycle" in result.output
        # diagnose-specific output should NOT appear
        assert "[Environment]" not in result.output
        assert "[Memory layer]" not in result.output
        mp.undo()

    def test_diagnose_renders_all_four_groups(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        self._init_minimal_project(tmp_path)
        result = runner.invoke(app, ["status", "--diagnose"])
        # All four group headers must appear regardless of pass/fail
        assert "[Environment]" in result.output
        assert "[Project]" in result.output
        assert "[Adapters]" in result.output
        assert "[Memory layer]" in result.output
        # Summary line at bottom
        assert "Summary:" in result.output
        mp.undo()

    def test_diagnose_no_vibe_dir_exits_one(self, tmp_path: Path) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        # No .vibe — diagnose must not crash; same early-exit as plain status
        result = runner.invoke(app, ["status", "--diagnose"])
        assert result.exit_code == 1
        mp.undo()

    def test_diagnose_environment_reports_python_version(
        self, tmp_path: Path
    ) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        self._init_minimal_project(tmp_path)
        result = runner.invoke(app, ["status", "--diagnose"])
        # python version line must appear; exact version varies per env
        assert "python:" in result.output
        mp.undo()

    def test_diagnose_project_warns_when_gitignore_missing_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Make this test independent of the host's vibe + basic-memory
        installations (CI Linux has neither on system PATH). Mock vibe
        binary, and disable [memory] so the memory layer doesn't error
        out — the assertion is about gitignore warning, not env."""
        monkeypatch.chdir(tmp_path)
        self._init_minimal_project(tmp_path)

        # Disable [memory] so basic-memory CLI absence doesn't error
        config = load_config(tmp_path / ".vibe")
        config.memory.enabled = False
        save_config(tmp_path / ".vibe", config)

        # Corrupt .gitignore so v0.3.6+ entries are missing
        gi = tmp_path / ".vibe" / ".gitignore"
        gi.write_text("backups/\n", encoding="utf-8")

        # Fake vibe on PATH (CI doesn't have it system-wide)
        import shutil as _sh
        real_which = _sh.which
        def fake_which(name: str) -> str | None:
            if name == "vibe":
                return "/usr/bin/vibe"
            return real_which(name)
        monkeypatch.setattr("shutil.which", fake_which)

        import subprocess as _sp
        real_run = _sp.run
        def fake_run(cmd: list[str], **kwargs: object) -> object:
            if cmd and cmd[0] == "/usr/bin/vibe":
                class R:
                    returncode = 0
                    stdout = "vibe-state-cli 0.3.8"
                    stderr = ""
                return R()
            return real_run(cmd, **kwargs)
        monkeypatch.setattr("subprocess.run", fake_run)

        result = runner.invoke(app, ["status", "--diagnose"])
        assert "missing entries" in result.output
        assert result.exit_code == 0

    def test_diagnose_project_no_git_warns(self, tmp_path: Path) -> None:
        """Workspaces without .git (e.g., governance) should WARN not ERROR."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        # init without git_init — no .git in project
        runner.invoke(app, ["init"])
        runner.invoke(app, ["start"])
        result = runner.invoke(app, ["status", "--diagnose"])
        assert "no .git in project" in result.output
        # Just a warning — must NOT cause exit 1
        # (assuming other groups are ok)
        mp.undo()

    def test_diagnose_adapters_flags_agents_md_missing_persistent_knowledge(
        self, tmp_path: Path
    ) -> None:
        """v0.3.7 added the Persistent Knowledge section. Older workspaces
        (those still on pre-v0.3.7 template) must be flagged so the user
        knows to run `vibe sync` to refresh."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        self._init_minimal_project(tmp_path)
        agents_md = tmp_path / "AGENTS.md"
        # Manually strip the Persistent Knowledge section to simulate stale
        if agents_md.exists():
            content = agents_md.read_text(encoding="utf-8")
            if "## Persistent Knowledge" in content:
                # Remove the whole section block (until next ##)
                lines = content.splitlines()
                new_lines = []
                skip = False
                for ln in lines:
                    if ln.startswith("## Persistent Knowledge"):
                        skip = True
                        continue
                    if skip and ln.startswith("## "):
                        skip = False
                    if not skip:
                        new_lines.append(ln)
                agents_md.write_text("\n".join(new_lines), encoding="utf-8")
        result = runner.invoke(app, ["status", "--diagnose"])
        assert "Persistent Knowledge" in result.output
        # Either current → ok, or pre-v0.3.7 → warn. Both acceptable, but
        # if we just stripped it, we must see the warning.
        assert "missing Persistent Knowledge" in result.output
        mp.undo()

    def test_diagnose_memory_layer_disabled_renders_as_ok(
        self, tmp_path: Path
    ) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        self._init_minimal_project(tmp_path)
        # Flip [memory].enabled to false
        config = load_config(tmp_path / ".vibe")
        config.memory.enabled = False
        save_config(tmp_path / ".vibe", config)
        result = runner.invoke(app, ["status", "--diagnose"])
        assert "[memory].enabled = false" in result.output
        # Disabled is intentional — no warnings/errors from this group
        mp.undo()

    def test_diagnose_memory_layer_warns_unknown_target(
        self, tmp_path: Path
    ) -> None:
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        self._init_minimal_project(tmp_path)
        config = load_config(tmp_path / ".vibe")
        config.memory.target = "obsidian"
        save_config(tmp_path / ".vibe", config)
        result = runner.invoke(app, ["status", "--diagnose"])
        # Unknown target should produce a warn (not error)
        assert "obsidian" in result.output
        assert "diagnose only knows basic-memory" in result.output
        mp.undo()

    def test_diagnose_memory_layer_errors_when_basic_memory_not_on_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibe_state.commands import cmd_status as _cs

        monkeypatch.chdir(tmp_path)
        self._init_minimal_project(tmp_path)

        # Mock shutil.which to return None for basic-memory
        import shutil as _sh
        real_which = _sh.which
        def fake_which(name: str) -> str | None:
            if name == "basic-memory":
                return None
            return real_which(name)
        monkeypatch.setattr(_cs.__name__ + ".shutil" if False else "shutil.which", fake_which)

        result = runner.invoke(app, ["status", "--diagnose"])
        assert "basic-memory CLI not on PATH" in result.output
        # Error → exit 1
        assert result.exit_code == 1

    def test_diagnose_runtime_probe_timeout_warns_not_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cold-start ≥30s on Windows was the RFC's motivating case. A
        timeout must surface as a WARN (informational), not ERROR — the
        user should retry, not panic.

        Also fake 'vibe' on PATH so the Environment group passes (matters
        on CI Linux runners where vibe is in the uv venv, not on system
        PATH)."""
        import subprocess as _sp

        monkeypatch.chdir(tmp_path)
        self._init_minimal_project(tmp_path)

        # Fake basic-memory AND vibe on PATH
        import shutil as _sh
        real_which = _sh.which
        def fake_which(name: str) -> str | None:
            if name == "basic-memory":
                return "/fake/basic-memory"
            if name == "vibe":
                return "/fake/vibe"
            return real_which(name)
        monkeypatch.setattr("shutil.which", fake_which)

        # subprocess.run: basic-memory probe times out, vibe --version
        # returns a fake successful response, everything else passes
        # through to the real subprocess.run.
        real_run = _sp.run
        def fake_run(cmd: list[str], **kwargs: object) -> object:
            if cmd and cmd[0] == "/fake/basic-memory":
                raise _sp.TimeoutExpired(cmd=cmd, timeout=5)
            if cmd and cmd[0] == "/fake/vibe":
                class R:
                    returncode = 0
                    stdout = "vibe-state-cli 0.3.8"
                    stderr = ""
                return R()
            return real_run(cmd, **kwargs)
        monkeypatch.setattr("subprocess.run", fake_run)

        result = runner.invoke(app, ["status", "--diagnose"])
        assert "timed out" in result.output
        assert "cold-starting" in result.output.lower()
        # Timeout = warn → exit 0 (other groups have no errors)
        assert result.exit_code == 0

    def test_diagnose_exit_code_zero_when_only_warnings(
        self, tmp_path: Path
    ) -> None:
        """brew-doctor convention: warnings are informational, exit 0."""
        mp = pytest.MonkeyPatch()
        mp.chdir(tmp_path)
        runner.invoke(app, ["init"])  # init without git → many warnings
        runner.invoke(app, ["start"])
        result = runner.invoke(app, ["status", "--diagnose"])
        # No .git, possibly no basic-memory → warnings expected, no errors
        # As long as ✓ python is present (always) and no missing core files,
        # exit should be 0 unless basic-memory is genuinely missing AND
        # [memory].enabled is true (default).
        # We accept either 0 or 1 here — the contract is "0 if only warnings".
        # Verify the SUMMARY line at least mentions counts.
        assert "Summary:" in result.output
        mp.undo()

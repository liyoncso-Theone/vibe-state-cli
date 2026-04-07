"""Git operations: available, cursor, errors, experiments."""

from __future__ import annotations

import subprocess
from pathlib import Path

from vibe_state.core.git_ops import (
    git_available,
    read_sync_cursor,
    write_sync_cursor,
)


def _git_init(p: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=p, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=p, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=p, capture_output=True)


class TestGitAvailability:
    def test_git_available(self) -> None:
        result = git_available()
        assert isinstance(result, bool)


class TestSyncCursor:
    def test_roundtrip(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        write_sync_cursor(vibe_dir, "abc123def")
        assert read_sync_cursor(vibe_dir) == "abc123def"

    def test_missing_returns_empty(self, tmp_path: Path) -> None:
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        assert read_sync_cursor(vibe_dir) == ""


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


class TestGitOpsLogAndDiff:
    def test_log_since_with_hash(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import get_head_hash, get_log_since

        _git_init(tmp_path)
        (tmp_path / "a.txt").write_text("1")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "first"],
            cwd=tmp_path, capture_output=True,
        )
        first_hash = get_head_hash(tmp_path)
        (tmp_path / "b.txt").write_text("2")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "second"],
            cwd=tmp_path, capture_output=True,
        )
        log = get_log_since(tmp_path, first_hash)
        assert len(log) == 1
        assert "second" in log[0]

    def test_diff_stat_with_hash(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import get_diff_stat, get_head_hash

        _git_init(tmp_path)
        (tmp_path / "a.txt").write_text("1")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "first"],
            cwd=tmp_path, capture_output=True,
        )
        h = get_head_hash(tmp_path)
        (tmp_path / "a.txt").write_text("modified")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "second"],
            cwd=tmp_path, capture_output=True,
        )
        stat = get_diff_stat(tmp_path, h)
        assert "a.txt" in stat


class TestExperimentDetection:
    def test_detects_autoresearch_commits(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import detect_experiment_commits

        _git_init(tmp_path)
        for i, msg in enumerate([
            "autoresearch: try lr=0.01",
            "normal commit",
            "autoresearch: revert - worse metric",
            "[autoresearch] try batch 32",
        ]):
            (tmp_path / f"f{i}.txt").write_text(str(i))
            subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", msg],
                cwd=tmp_path, capture_output=True,
            )
        experiments = detect_experiment_commits(tmp_path, since_hash="")
        assert len(experiments) == 3
        kept = [e for e in experiments if not e.is_revert]
        reverted = [e for e in experiments if e.is_revert]
        assert len(kept) == 2
        assert len(reverted) == 1

    def test_no_experiments(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import detect_experiment_commits

        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: normal"],
            cwd=tmp_path, capture_output=True,
        )
        assert detect_experiment_commits(tmp_path) == []

    def test_single_word_commit_skipped(self, tmp_path: Path) -> None:
        from vibe_state.core.git_ops import detect_experiment_commits

        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "singleword"],
            cwd=tmp_path, capture_output=True,
        )
        exps = detect_experiment_commits(tmp_path)
        assert exps == []

    def test_commit_with_empty_message(self, tmp_path: Path) -> None:
        """A commit line with no space (single word) is skipped."""
        from vibe_state.core.git_ops import detect_experiment_commits

        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "--allow-empty-message", "-m", ""],
            cwd=tmp_path, capture_output=True,
        )
        experiments = detect_experiment_commits(tmp_path)
        assert experiments == []

    def test_revert_only_matches_prefix_not_body(self, tmp_path: Path) -> None:
        """'revert' in the message body (not prefix) must NOT flag as reverted.

        e.g., 'experiment: fix revert payment issue' is a KEPT experiment,
        because 'revert' appears in the body describing the task, not as
        the experiment action prefix.
        """
        from vibe_state.core.git_ops import detect_experiment_commits

        _git_init(tmp_path)
        for msg in [
            "experiment: revert - metric dropped",  # prefix revert → REVERTED
            "experiment: fix revert payment issue",  # body revert → KEPT
            "autoresearch: reset to baseline",  # prefix reset → REVERTED
            "autoresearch: implement password reset flow",  # body reset → KEPT
        ]:
            (tmp_path / "f.txt").write_text(msg)
            subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", msg],
                cwd=tmp_path, capture_output=True,
            )

        exps = detect_experiment_commits(tmp_path)
        assert len(exps) == 4
        # git log is newest-first, so reverse order from commit sequence
        msgs = {e.message: e.is_revert for e in exps}
        assert msgs["experiment: revert - metric dropped"] is True
        assert msgs["experiment: fix revert payment issue"] is False
        assert msgs["autoresearch: reset to baseline"] is True
        assert msgs["autoresearch: implement password reset flow"] is False

    def test_custom_patterns_from_config(self, tmp_path: Path) -> None:
        """User-defined patterns in config override defaults."""
        from vibe_state.core.git_ops import detect_experiment_commits

        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "[bot] try new approach"],
            cwd=tmp_path, capture_output=True,
        )

        # Default patterns won't match [bot]
        exps = detect_experiment_commits(tmp_path)
        assert len(exps) == 0

        # Custom pattern matches
        exps = detect_experiment_commits(
            tmp_path, commit_patterns=["[bot]"]
        )
        assert len(exps) == 1

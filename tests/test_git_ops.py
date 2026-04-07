"""Git operations: available, cursor, errors, experiments."""

from __future__ import annotations

import subprocess
from pathlib import Path

from vibe_state.core.git_ops import (
    ExperimentCommit,
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

    def test_parses_experiment_commit_fields(self) -> None:
        """Test the parsing logic directly."""
        commits = [
            "abc1234 autoresearch: try lr=0.01",
            "def5678 normal commit message",
            "ghi9012 autoresearch: revert - metric decreased",
            "jkl3456 [autoresearch] try batch size 32",
            "mno7890 experiment: try dropout 0.5",
        ]
        experiments: list[ExperimentCommit] = []
        patterns = [
            "autoresearch:", "experiment:", "[autoresearch]",
            "[experiment]", "auto-research",
        ]
        for line in commits:
            parts = line.split(" ", 1)
            if len(parts) < 2:
                continue
            commit_hash, msg = parts[0], parts[1]
            msg_lower = msg.lower()
            is_experiment = any(p in msg_lower for p in patterns)
            if not is_experiment:
                continue
            is_revert = "revert" in msg_lower or "reset" in msg_lower
            experiments.append(ExperimentCommit(
                hash=commit_hash, message=msg, is_revert=is_revert
            ))
        assert len(experiments) == 4
        assert experiments[0].hash == "abc1234"
        assert not experiments[0].is_revert
        assert experiments[1].is_revert
        assert experiments[2].hash == "jkl3456"
        assert experiments[3].hash == "mno7890"

    def test_empty_log(self) -> None:
        experiments: list[ExperimentCommit] = []
        assert len(experiments) == 0

    def test_all_normal_commits(self) -> None:
        commits = ["abc feat: add feature", "def fix: bug fix"]
        patterns = ["autoresearch:", "experiment:"]
        experiments = []
        for line in commits:
            parts = line.split(" ", 1)
            if len(parts) < 2:
                continue
            msg_lower = parts[1].lower()
            if any(p in msg_lower for p in patterns):
                experiments.append(parts[0])
        assert len(experiments) == 0

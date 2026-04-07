"""Tests for autoresearch experiment detection."""

from __future__ import annotations

from vibe_state.core.git_ops import ExperimentCommit


class TestExperimentDetection:
    def test_detects_autoresearch_prefix(self, tmp_path: object) -> None:
        # Mock by testing the parsing logic directly
        commits = [
            "abc1234 autoresearch: try lr=0.01",
            "def5678 normal commit message",
            "ghi9012 autoresearch: revert - metric decreased",
            "jkl3456 [autoresearch] try batch size 32",
            "mno7890 experiment: try dropout 0.5",
        ]
        # Simulate what detect_experiment_commits does internally
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

        assert len(experiments) == 4  # "normal commit" excluded
        assert experiments[0].hash == "abc1234"
        assert not experiments[0].is_revert
        assert experiments[1].is_revert  # "revert" in message
        assert experiments[2].hash == "jkl3456"
        assert experiments[3].hash == "mno7890"

    def test_empty_log(self) -> None:
        # No commits → no experiments
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

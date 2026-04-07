"""Tests for config management."""

from __future__ import annotations

from pathlib import Path

from vibe_state.config import VibeConfig, load_config, save_config


def test_default_config() -> None:
    config = VibeConfig()
    assert config.vibe.version == 1
    assert config.vibe.lang == "en"
    assert config.state.compact_threshold == 150
    assert config.state.stale_task_days == 30
    assert config.adapters.enabled == ["agents_md"]
    assert config.adapters.auto_detect is True
    assert config.git.enabled is True
    assert config.git.auto_commit is False


def test_save_and_load_config(tmp_path: Path) -> None:
    config = VibeConfig()
    config.adapters.enabled = ["agents_md", "claude"]
    save_config(tmp_path, config)

    loaded = load_config(tmp_path)
    assert loaded.adapters.enabled == ["agents_md", "claude"]


def test_load_missing_config(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.vibe.version == 1  # Returns defaults

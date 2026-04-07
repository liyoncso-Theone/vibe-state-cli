"""Config: defaults, save/load, malformed TOML, dedup."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibe_state.config import AdaptersSection, VibeConfig, load_config, save_config
from vibe_state.core.templates import render_template


class TestConfigDefaults:
    def test_default_config_values(self) -> None:
        config = VibeConfig()
        assert config.vibe.version == 1
        assert config.vibe.lang == "en"
        assert config.state.compact_threshold == 150
        assert config.state.stale_task_days == 30
        assert config.adapters.enabled == ["agents_md"]
        assert config.adapters.auto_detect is True
        assert config.git.enabled is True
        assert config.git.auto_commit is False

    def test_fresh_config_no_dupes(self) -> None:
        c = VibeConfig()
        assert c.adapters.enabled == ["agents_md"]


class TestConfigSaveLoad:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        config = VibeConfig()
        config.adapters.enabled = ["agents_md", "claude"]
        save_config(tmp_path, config)
        loaded = load_config(tmp_path)
        assert loaded.adapters.enabled == ["agents_md", "claude"]

    def test_load_missing_config_returns_defaults(self, tmp_path: Path) -> None:
        config = load_config(tmp_path)
        assert config.vibe.version == 1

    def test_save_preserves_header_comments(self, tmp_path: Path) -> None:
        """Header comments in config.toml must survive save_config."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            "# Team config — do not change compact_threshold!\n"
            "# Updated by DevOps on 2026-04-01\n"
            "\n"
            '[vibe]\nversion = 1\nlang = "en"\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        config.adapters.enabled = ["agents_md", "cursor"]
        save_config(tmp_path, config)

        saved = config_path.read_text(encoding="utf-8")
        assert "# Team config" in saved
        assert "# Updated by DevOps" in saved
        assert "cursor" in saved


class TestConfigMalformed:
    def test_malformed_toml_halts_execution(self, tmp_path: Path) -> None:
        """Corrupt config must STOP execution, not silently use defaults."""
        config_path = tmp_path / "config.toml"
        config_path.write_text("INVALID{{{TOML", encoding="utf-8")
        with pytest.raises(SystemExit):
            load_config(tmp_path)


class TestConfigDedup:
    def test_dedup_via_model_post_init(self) -> None:
        config = VibeConfig()
        config.adapters.enabled = ["a", "b", "a", "c", "b"]
        config.adapters.model_post_init(None)
        assert config.adapters.enabled == ["a", "b", "c"]

    def test_dedup_via_pydantic(self) -> None:
        section = AdaptersSection(enabled=["a", "b", "a"])
        assert section.enabled == ["a", "b"]


class TestTemplateFallback:
    def test_unsupported_lang_falls_back(self) -> None:
        result = render_template("vibe.md.j2", lang="fr")
        assert "Project Constitution" in result  # English fallback

    def test_zh_tw_uses_chinese(self) -> None:
        result = render_template("vibe.md.j2", lang="zh-TW")
        assert "專案憲法" in result

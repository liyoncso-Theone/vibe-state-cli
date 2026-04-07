"""Config: defaults, save/load, malformed TOML, dedup."""

from __future__ import annotations

from pathlib import Path

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


class TestConfigMalformed:
    def test_malformed_toml_returns_defaults(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text("INVALID{{{TOML", encoding="utf-8")
        config = load_config(tmp_path)
        assert config.vibe.version == 1


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

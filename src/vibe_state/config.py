"""Configuration management for .vibe/config.toml."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger("vibe.config")


class VibeSection(BaseModel):
    version: int = 1
    lang: str = "en"


class StateSection(BaseModel):
    compact_threshold: int = Field(default=150, ge=10, le=10000)
    stale_task_days: int = Field(default=30, ge=1, le=365)


class AdaptersSection(BaseModel):
    enabled: list[str] = Field(default_factory=lambda: ["agents_md"])
    auto_detect: bool = True

    def model_post_init(self, __context: object) -> None:
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for name in self.enabled:
            if name not in seen:
                seen.add(name)
                deduped.append(name)
        self.enabled = deduped


class GitSection(BaseModel):
    enabled: bool = True
    auto_commit: bool = False


class VibeConfig(BaseModel):
    vibe: VibeSection = Field(default_factory=VibeSection)
    state: StateSection = Field(default_factory=StateSection)
    adapters: AdaptersSection = Field(default_factory=AdaptersSection)
    git: GitSection = Field(default_factory=GitSection)


def load_config(vibe_dir: Path) -> VibeConfig:
    """Load config from .vibe/config.toml, or return defaults."""
    config_path = vibe_dir / "config.toml"
    if not config_path.exists():
        logger.debug("No config.toml found, using defaults")
        return VibeConfig()

    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib  # pragma: no cover

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        return VibeConfig(**data)
    except Exception as e:
        from rich.console import Console

        Console().print(
            f"[red]Error:[/] Failed to parse config.toml: {e}\n"
            f"[dim]Using defaults. Fix or delete .vibe/config.toml to resolve.[/]"
        )
        return VibeConfig()


def save_config(vibe_dir: Path, config: VibeConfig) -> None:
    """Save config to .vibe/config.toml."""
    import tomli_w

    config_path = vibe_dir / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "wb") as f:
        tomli_w.dump(config.model_dump(), f)

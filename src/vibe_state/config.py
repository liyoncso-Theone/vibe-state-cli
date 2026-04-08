"""Configuration management for .vibe/config.toml."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from vibe_state.core.constants import DEFAULT_EXPERIMENT_PATTERNS, DEFAULT_REVERT_PREFIXES

logger = logging.getLogger("vibe.config")


class ConfigParseError(Exception):
    """Raised when config.toml cannot be parsed."""


class VibeSection(BaseModel):
    version: int = 1
    lang: str = "en"


class StateSection(BaseModel):
    compact_threshold: int = Field(default=150, ge=10, le=10000)
    stale_task_days: int = Field(default=30, ge=1, le=365)


class AdaptersSection(BaseModel):
    enabled: list[str] = Field(default_factory=lambda: ["agents_md"])

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


class ExperimentsSection(BaseModel):
    """Configuration for autoresearch experiment detection."""

    # Patterns to match in commit messages (case-insensitive)
    commit_patterns: list[str] = Field(
        default_factory=lambda: list(DEFAULT_EXPERIMENT_PATTERNS)
    )
    revert_prefixes: list[str] = Field(
        default_factory=lambda: list(DEFAULT_REVERT_PREFIXES)
    )


class VibeConfig(BaseModel):
    vibe: VibeSection = Field(default_factory=VibeSection)
    state: StateSection = Field(default_factory=StateSection)
    adapters: AdaptersSection = Field(default_factory=AdaptersSection)
    git: GitSection = Field(default_factory=GitSection)
    experiments: ExperimentsSection = Field(default_factory=ExperimentsSection)


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
        raise ConfigParseError(
            f"Failed to parse config.toml: {e}\n"
            f"Fix or delete .vibe/config.toml to continue."
        ) from e


def save_config(vibe_dir: Path, config: VibeConfig) -> None:
    """Save config to .vibe/config.toml, preserving header comments."""
    import tomli_w

    config_path = vibe_dir / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Preserve header comment block from existing file
    header_lines: list[str] = []
    if config_path.exists():
        for line in config_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped == "":
                header_lines.append(line)
            else:
                break

    new_data = tomli_w.dumps(config.model_dump())
    header = "\n".join(header_lines) + "\n" if header_lines else ""
    config_path.write_text(header + new_data, encoding="utf-8", newline="\n")

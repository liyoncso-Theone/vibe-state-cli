"""Shared constants — single source of truth for default values."""

from __future__ import annotations

# Autoresearch commit detection patterns
DEFAULT_EXPERIMENT_PATTERNS: list[str] = [
    "autoresearch:",
    "experiment:",
    "[autoresearch]",
    "[experiment]",
    "auto-research",
]

DEFAULT_REVERT_PREFIXES: list[str] = [
    "revert",
    "reset",
    "rollback",
    "undo",
]

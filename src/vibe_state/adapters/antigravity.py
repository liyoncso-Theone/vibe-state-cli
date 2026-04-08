"""Antigravity / Gemini CLI adapter — GEMINI.md (plain Markdown, no frontmatter)."""

from __future__ import annotations

from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter


@register_adapter
class AntigravityAdapter(AdapterBase):
    name = "antigravity"
    REQUIRED_FIELDS: set[str] = set()  # No frontmatter for GEMINI.md

    def detect(self, project_root: Path) -> bool:
        return (project_root / "GEMINI.md").exists()

    def emit(self, ctx: AdapterContext) -> list[Path]:
        if "GEMINI.md" in ctx.user_owned_files:
            return []
        lines = [f"# GEMINI.md — {ctx.project_name}", ""]
        if "agents_md" in ctx.enabled_adapters:
            # @import requires Antigravity/Gemini CLI >= 1.20.3
            # Include compact fallback so older versions still work
            lines += ["@AGENTS.md", "", "## Antigravity-Specific", ""]
            lines += self._build_common_body(ctx, mode="compact")
        else:
            lines += ["## Project", ""]
            lines += self._build_common_body(ctx, mode="compact")
        lines += [""]
        content = "\n".join(lines)
        return [self._write_file(ctx.project_root / "GEMINI.md", content)]

    def clean(self, project_root: Path) -> list[Path]:
        p = project_root / "GEMINI.md"
        return [p] if p.exists() else []

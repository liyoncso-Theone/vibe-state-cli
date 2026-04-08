"""Roo Code adapter — .roo/rules/*.md files (no frontmatter)."""

from __future__ import annotations

from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter


@register_adapter
class RooAdapter(AdapterBase):
    name = "roo"
    REQUIRED_FIELDS: set[str] = set()

    def detect(self, project_root: Path) -> bool:
        return (project_root / ".roo").is_dir()

    def emit(self, ctx: AdapterContext) -> list[Path]:
        lines = [f"# Vibe Standards — {ctx.project_name}", ""]
        # Roo Code — use compact mode
        lines += self._build_common_body(ctx, mode="compact")
        return [self._write_file(
            ctx.project_root / ".roo" / "rules" / "01-vibe-standards.md",
            "\n".join(lines),
        )]

    def clean(self, project_root: Path) -> list[Path]:
        t = project_root / ".roo" / "rules" / "01-vibe-standards.md"
        return [t] if t.exists() else []

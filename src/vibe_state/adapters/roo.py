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
        # v0.3.6: AGENTS.md is now the Linux Foundation standard
        # (2025-12). When co-enabled, defer to it via a one-line shim.
        mode = "slim" if "agents_md" in ctx.enabled_adapters else "compact"
        lines += self._build_common_body(ctx, mode=mode)
        return [self._write_file(
            ctx.project_root / ".roo" / "rules" / "01-vibe-standards.md",
            "\n".join(lines),
        )]

    def clean(self, project_root: Path) -> list[Path]:
        t = project_root / ".roo" / "rules" / "01-vibe-standards.md"
        return [t] if t.exists() else []

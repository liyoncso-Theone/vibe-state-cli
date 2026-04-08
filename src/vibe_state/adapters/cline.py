"""Cline adapter — .clinerules/*.md files."""

from __future__ import annotations

import re
from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter


@register_adapter
class ClineAdapter(AdapterBase):
    name = "cline"
    REQUIRED_FIELDS = {"paths"}

    def detect(self, project_root: Path) -> bool:
        return (project_root / ".clinerules").is_dir()

    def emit(self, ctx: AdapterContext) -> list[Path]:
        lines = [
            "---",
            "paths:",
            '  - "**/*"',
            "---",
            "",
            f"# Vibe Standards — {ctx.project_name}",
            "",
        ]
        # Cline cannot reliably read AGENTS.md — use compact mode
        lines += self._build_common_body(ctx, mode="compact")
        content = "\n".join(lines)
        if not self.validate(content):
            self._warn_validation("Cline rule")
        return [self._write_file(
            ctx.project_root / ".clinerules" / "01-vibe-standards.md", content
        )]

    def clean(self, project_root: Path) -> list[Path]:
        t = project_root / ".clinerules" / "01-vibe-standards.md"
        return [t] if t.exists() else []

    def validate(self, output: str) -> bool:
        fm = re.match(r"^---\n(.*?)\n---", output, re.DOTALL)
        return bool(fm and "paths" in fm.group(1))

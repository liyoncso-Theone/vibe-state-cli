"""Cursor adapter — .cursor/rules/*.mdc files."""

from __future__ import annotations

import re
from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter


@register_adapter
class CursorAdapter(AdapterBase):
    name = "cursor"
    REQUIRED_FIELDS = {"alwaysApply", "description"}

    def detect(self, project_root: Path) -> bool:
        return (project_root / ".cursor").is_dir() or (project_root / ".cursorrules").exists()

    def emit(self, ctx: AdapterContext) -> list[Path]:
        desc = f"Vibe standards for {ctx.project_name}"
        lines = [
            "---",
            "alwaysApply: true",
            f'description: "{desc}"',
            'globs: ["**/*"]',
            "---",
            "",
            f"# Vibe Standards — {ctx.project_name}",
            "",
        ]
        # Cursor cannot read AGENTS.md — use compact mode (inline standards)
        lines += self._build_common_body(ctx, mode="compact")
        content = "\n".join(lines)
        if not self.validate(content):
            self._warn_validation("Cursor .mdc")
        return [self._write_file(
            ctx.project_root / ".cursor" / "rules" / "vibe-standards.mdc", content
        )]

    def clean(self, project_root: Path) -> list[Path]:
        t = project_root / ".cursor" / "rules" / "vibe-standards.mdc"
        return [t] if t.exists() else []

    def validate(self, output: str) -> bool:
        fm = re.match(r"^---\n(.*?)\n---", output, re.DOTALL)
        if not fm:
            return False
        return all(f in fm.group(1) for f in self.REQUIRED_FIELDS)

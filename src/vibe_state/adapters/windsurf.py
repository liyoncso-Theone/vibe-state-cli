"""Windsurf adapter — .windsurf/rules/*.md files."""

from __future__ import annotations

import re
from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter

VALID_TRIGGERS = {"always_on", "model_decision", "glob", "manual"}


@register_adapter
class WindsurfAdapter(AdapterBase):
    name = "windsurf"
    REQUIRED_FIELDS = {"trigger", "description"}

    def detect(self, project_root: Path) -> bool:
        return (project_root / ".windsurf").is_dir() or (project_root / ".windsurfrules").exists()

    def emit(self, ctx: AdapterContext) -> list[Path]:
        desc = f"Vibe standards for {ctx.project_name}"
        lines = [
            "---",
            "trigger: always_on",
            f'description: "{desc}"',
            "---",
            "",
            f"# Vibe Standards — {ctx.project_name}",
            "",
        ]
        slim = "agents_md" in ctx.enabled_adapters
        lines += self._build_common_body(ctx, slim=slim)
        content = "\n".join(lines)
        if not self.validate(content):
            self._warn_validation("Windsurf rule")
        return [self._write_file(
            ctx.project_root / ".windsurf" / "rules" / "vibe-standards.md", content
        )]

    def clean(self, project_root: Path) -> list[Path]:
        t = project_root / ".windsurf" / "rules" / "vibe-standards.md"
        return [t] if t.exists() else []

    def validate(self, output: str) -> bool:
        fm = re.match(r"^---\n(.*?)\n---", output, re.DOTALL)
        if not fm:
            return False
        text = fm.group(1)
        if "trigger" not in text or "description" not in text:
            return False
        return any(t in text for t in VALID_TRIGGERS)

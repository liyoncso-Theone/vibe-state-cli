"""AGENTS.md adapter — Linux Foundation / AAIF universal standard."""

from __future__ import annotations

from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter

MAX_SIZE_BYTES = 32 * 1024


@register_adapter
class AgentsMdAdapter(AdapterBase):
    name = "agents_md"
    REQUIRED_FIELDS: set[str] = set()

    def detect(self, project_root: Path) -> bool:
        return (project_root / "AGENTS.md").exists()

    def emit(self, ctx: AdapterContext) -> list[Path]:
        if "AGENTS.md" in ctx.user_owned_files:
            return []  # User has their own, don't overwrite

        lines = [
            f"# AGENTS.md — {ctx.project_name}",
            "",
            "## Project",
            "",
        ]
        lines += self._build_common_body(ctx)
        content = "\n".join(lines)
        if not self.validate(content):
            self._warn_validation("AGENTS.md (>32KiB)")
        return [self._write_file(ctx.project_root / "AGENTS.md", content)]

    def clean(self, project_root: Path) -> list[Path]:
        p = project_root / "AGENTS.md"
        return [p] if p.exists() else []

    def validate(self, output: str) -> bool:
        return len(output.encode("utf-8")) <= MAX_SIZE_BYTES

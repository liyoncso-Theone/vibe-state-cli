"""GitHub Copilot adapter — .github/copilot-instructions.md + instructions/."""

from __future__ import annotations

import re
from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter


@register_adapter
class CopilotAdapter(AdapterBase):
    name = "copilot"
    REQUIRED_FIELDS = {"applyTo"}

    def detect(self, project_root: Path) -> bool:
        return (project_root / ".github" / "copilot-instructions.md").exists()

    def emit(self, ctx: AdapterContext) -> list[Path]:
        files: list[Path] = []

        # Copilot cannot read AGENTS.md — use compact mode (4000 char limit)
        # Main instructions (no frontmatter)
        main = [f"# Copilot Instructions — {ctx.project_name}", ""]
        main += self._build_common_body(ctx, mode="compact")
        files.append(self._write_file(
            ctx.project_root / ".github" / "copilot-instructions.md", "\n".join(main)
        ))

        # Path-scoped instructions
        scoped = ["---", 'applyTo: "**/*"', "---", "", "# Vibe Standards", ""]
        scoped += self._build_common_body(ctx, mode="compact")
        content = "\n".join(scoped)
        if not self.validate(content):
            self._warn_validation("Copilot instructions")
        files.append(self._write_file(
            ctx.project_root / ".github" / "instructions" / "vibe-standards.instructions.md",
            content,
        ))
        return files

    def clean(self, project_root: Path) -> list[Path]:
        files: list[Path] = []
        for p in [
            project_root / ".github" / "copilot-instructions.md",
            project_root / ".github" / "instructions" / "vibe-standards.instructions.md",
        ]:
            if p.exists():
                files.append(p)
        return files

    def validate(self, output: str) -> bool:
        fm = re.match(r"^---\n(.*?)\n---", output, re.DOTALL)
        if not fm:
            return True  # Main file has no frontmatter
        return "applyTo" in fm.group(1)

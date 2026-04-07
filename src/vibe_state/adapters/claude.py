"""Claude Code adapter — CLAUDE.md + .claude/rules/*.md."""

from __future__ import annotations

import json
from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter


@register_adapter
class ClaudeAdapter(AdapterBase):
    name = "claude"
    REQUIRED_FIELDS: set[str] = set()

    def detect(self, project_root: Path) -> bool:
        return (project_root / ".claude").is_dir() or (project_root / "CLAUDE.md").exists()

    def emit(self, ctx: AdapterContext) -> list[Path]:
        files: list[Path] = []

        # CLAUDE.md — skip if user already has one (migration preserves theirs)
        if "CLAUDE.md" not in ctx.user_owned_files:
            lines = [f"# CLAUDE.md — {ctx.project_name}", ""]
            if "agents_md" in ctx.enabled_adapters:
                lines += ["@AGENTS.md", "", "## Claude-Specific", ""]
            else:
                lines += ["## Project", ""]
                lines += self._build_common_body(ctx)

            lines += [
                "## Vibe Workflow",
                "",
                "Read `.vibe/VIBE.md` for the full protocol.",
                "**Checkpoint**: After each task, mark `[x]` in `state/tasks.md`"
                " and append to `state/current.md`.",
                "**Reality-First**: When memory conflicts with git, trust git.",
                "",
            ]
            files.append(self._write_file(ctx.project_root / "CLAUDE.md", "\n".join(lines)))

        # .claude/rules/vibe-standards.md (slim when AGENTS.md also enabled)
        slim = "agents_md" in ctx.enabled_adapters
        rules = ["---", 'paths: ["**/*"]', "---", "", "# Vibe Standards", ""]
        rules += self._build_common_body(ctx, slim=slim)
        files.append(self._write_file(
            ctx.project_root / ".claude" / "rules" / "vibe-standards.md",
            "\n".join(rules),
        ))

        # .claude/settings.json (only if not exists)
        settings_path = ctx.project_root / ".claude" / "settings.json"
        if not settings_path.exists():
            files.append(self._write_file(
                settings_path, json.dumps({"permissions": {}, "hooks": {}}, indent=2) + "\n"
            ))

        return files

    def clean(self, project_root: Path) -> list[Path]:
        files: list[Path] = []
        for p in [
            project_root / "CLAUDE.md",
            project_root / ".claude" / "rules" / "vibe-standards.md",
        ]:
            if p.exists():
                files.append(p)
        return files

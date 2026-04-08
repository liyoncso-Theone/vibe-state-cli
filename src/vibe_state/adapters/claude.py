"""Claude Code adapter — CLAUDE.md + .claude/rules/*.md + skills."""

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

        # CLAUDE.md — skip if user's original is preserved
        if "CLAUDE.md" not in ctx.user_owned_files:
            lines = [f"# CLAUDE.md — {ctx.project_name}", ""]
            if "agents_md" in ctx.enabled_adapters:
                lines += ["@AGENTS.md", "", "## Claude-Specific", ""]
            else:
                lines += ["## Project", ""]
                lines += self._build_common_body(ctx, mode="full")
            lines += [""]
            files.append(self._write_file(ctx.project_root / "CLAUDE.md", "\n".join(lines)))

        # .claude/rules/vibe-standards.md (slim when AGENTS.md co-enabled)
        mode = "slim" if "agents_md" in ctx.enabled_adapters else "full"
        rules = ["---", 'paths: ["**/*"]', "---", "", "# Vibe Standards", ""]
        rules += self._build_common_body(ctx, mode=mode)
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

        # .claude/skills/ — slash commands for vibe CLI
        skills = {
            "vibe-init": (
                "Initialize vibe project state tracking (.vibe/ directory)",
                "Run in terminal:\n\n```bash\nvibe init\n```\n\nReport the result.",
            ),
            "vibe-start": (
                "Start a vibe session — load project state and context",
                "Run in terminal:\n\n```bash\nvibe start\n```\n\n"
                "Then read `.vibe/state/current.md` and `.vibe/state/tasks.md`"
                " for full context.",
            ),
            "vibe-sync": (
                "Sync git activity into vibe state and run C.L.E.A.R. checklist",
                "Run in terminal:\n\n```bash\nvibe sync\n```\n\nReport the sync result.",
            ),
            "vibe-status": (
                "Show current vibe lifecycle state and project status",
                "Run in terminal:\n\n```bash\nvibe status\n```\n\nReport the status.",
            ),
            "vibe-adapt": (
                "Add or remove adapter config files for AI/IDE tools",
                "Run in terminal:\n\n```bash\nvibe adapt\n```\n\nReport what changed.",
            ),
        }
        for skill_name, (desc, body) in skills.items():
            skill_dir = ctx.project_root / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            content = f"---\nname: {skill_name}\ndescription: {desc}\n---\n\n{body}\n"
            skill_path = skill_dir / "SKILL.md"
            files.append(self._write_file(skill_path, content))

        return files

    def clean(self, project_root: Path) -> list[Path]:
        files: list[Path] = []
        for p in [
            project_root / "CLAUDE.md",
            project_root / ".claude" / "rules" / "vibe-standards.md",
        ]:
            if p.exists():
                files.append(p)
        for skill_name in ("vibe-init", "vibe-start", "vibe-sync", "vibe-status", "vibe-adapt"):
            skill_file = project_root / ".claude" / "skills" / skill_name / "SKILL.md"
            if skill_file.exists():
                files.append(skill_file)
        return files

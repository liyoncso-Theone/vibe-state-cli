"""Antigravity / Gemini CLI adapter.

v0.3.6 transition: Google announced that Gemini CLI is being replaced by
Antigravity CLI (`agy`) on 2026-06-18. The new CLI reads AGENTS.md and
`.agents/` instead of GEMINI.md and `.gemini/`. This adapter writes the
new `.agents/skills/` layout (for forward-compat) AND keeps writing
GEMINI.md with a deprecation banner (for transition users still on Gemini
CLI). GEMINI.md output will be removed entirely in a future release after
the 2026-06-18 cutover.

Reference: https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
"""

from __future__ import annotations

from pathlib import Path

from vibe_state.adapters.base import AdapterBase, AdapterContext
from vibe_state.adapters.registry import register_adapter

_GEMINI_DEPRECATION_BANNER = (
    "> ⚠️ **GEMINI.md is deprecated** — Google is transitioning Gemini CLI to\n"
    "> Antigravity CLI (`agy`) on **2026-06-18**. The new CLI reads "
    "`AGENTS.md`\n> and `.agents/skills/` instead. After the cutover, vibe will "
    "stop\n> writing this file. Migrate when convenient — `vibe adapt --sync` "
    "will\n> regenerate the new layout for you.\n"
)

_AGENT_SKILLS = {
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


@register_adapter
class AntigravityAdapter(AdapterBase):
    name = "antigravity"
    REQUIRED_FIELDS: set[str] = set()  # No frontmatter for GEMINI.md

    def detect(self, project_root: Path) -> bool:
        return (
            (project_root / "GEMINI.md").exists()
            or (project_root / ".agents").is_dir()
        )

    def emit(self, ctx: AdapterContext) -> list[Path]:
        files: list[Path] = []

        # ── Antigravity CLI (.agents/skills/) — the forward path ──
        for skill_name, (desc, body) in _AGENT_SKILLS.items():
            skill_dir = ctx.project_root / ".agents" / "skills" / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            content = (
                f"---\nname: {skill_name}\ndescription: {desc}\n---\n\n{body}\n"
            )
            files.append(self._write_file(skill_dir / "SKILL.md", content))

        # ── GEMINI.md — kept until 2026-06-18 cutover for transition users ──
        if "GEMINI.md" not in ctx.user_owned_files:
            lines = [
                f"# GEMINI.md — {ctx.project_name}",
                "",
                _GEMINI_DEPRECATION_BANNER,
                "",
            ]
            if "agents_md" in ctx.enabled_adapters:
                # @import requires Antigravity/Gemini CLI >= 1.20.3
                # Include compact fallback so older versions still work
                lines += ["@AGENTS.md", "", "## Antigravity-Specific", ""]
                lines += self._build_common_body(ctx, mode="compact")
            else:
                lines += ["## Project", ""]
                lines += self._build_common_body(ctx, mode="compact")
            lines += [""]
            files.append(
                self._write_file(ctx.project_root / "GEMINI.md", "\n".join(lines))
            )

        return files

    def clean(self, project_root: Path) -> list[Path]:
        files: list[Path] = []
        gemini = project_root / "GEMINI.md"
        if gemini.exists():
            files.append(gemini)
        for skill_name in _AGENT_SKILLS:
            skill_file = (
                project_root / ".agents" / "skills" / skill_name / "SKILL.md"
            )
            if skill_file.exists():
                files.append(skill_file)
        return files

"""Base adapter interface for all AI/IDE tool adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AdapterContext:
    """Context passed to adapters for file generation."""

    project_root: Path
    vibe_dir: Path
    standards: str = ""
    architecture: str = ""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    project_name: str = ""
    enabled_adapters: list[str] = field(default_factory=list)
    user_owned_files: list[str] = field(default_factory=list)
    state_summary: str = ""  # Compact digest injected into adapter output


def _sanitize(value: str) -> str:
    """Strip control chars from user-controlled strings (project names)."""
    return "".join(c for c in value if c.isprintable() and c not in "\n\r")


def build_adapter_context(project_root: Path) -> AdapterContext:
    """Build AdapterContext from .vibe/ config + state files."""
    vibe_dir = project_root / ".vibe"

    def _read(rel: str) -> str:
        p = vibe_dir / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""

    from vibe_state.config import load_config
    from vibe_state.core.summary import build_state_summary

    config = load_config(vibe_dir)
    summary = build_state_summary(vibe_dir)

    # Parse languages/frameworks from architecture.md
    languages: list[str] = []
    frameworks: list[str] = []
    arch = _read("state/architecture.md")
    for line in arch.splitlines():
        if line.strip().startswith("- Language:"):
            lang_val = line.split(":", 1)[1].strip()
            if lang_val:
                languages.append(lang_val)
        if line.strip().startswith("- Framework:"):
            fw_val = line.split(":", 1)[1].strip()
            if fw_val:
                frameworks.append(fw_val)

    return AdapterContext(
        project_root=project_root,
        vibe_dir=vibe_dir,
        standards=_read("state/standards.md"),
        architecture=_read("state/architecture.md"),
        languages=[_sanitize(lang) for lang in languages],
        frameworks=[_sanitize(fw) for fw in frameworks],
        project_name=_sanitize(project_root.name),
        enabled_adapters=config.adapters.enabled,
        state_summary=summary,
    )


class AdapterBase(ABC):
    """Abstract base class for all adapters."""

    name: str = ""
    REQUIRED_FIELDS: set[str] = set()

    @abstractmethod
    def detect(self, project_root: Path) -> bool:
        """Detect if this tool's config already exists in the project."""

    @abstractmethod
    def emit(self, ctx: AdapterContext) -> list[Path]:
        """Generate config files for this tool. Returns list of created file paths."""

    @abstractmethod
    def clean(self, project_root: Path) -> list[Path]:
        """Return list of files that would be removed for this adapter."""

    def validate(self, output: str) -> bool:
        """Validate emitted file content. Override for frontmatter checks."""
        return True

    def _write_file(self, path: Path, content: str) -> Path:
        """Write content to file with managed marker. Skip if unchanged.

        Uses retry to handle IDE/antivirus file locks on Windows.
        """
        import time

        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in (".md", ".mdc"):
            content = content.rstrip() + "\n\n<!-- vibe-state-cli:managed -->\n"
        # Skip write if content is identical (avoid unnecessary git diffs)
        if path.exists():
            try:
                if path.read_text(encoding="utf-8") == content:
                    return path
            except (OSError, UnicodeDecodeError):
                pass
        # Retry on PermissionError (IDE or antivirus may hold the file)
        for attempt in range(3):
            try:
                path.write_text(content, encoding="utf-8", newline="\n")
                return path
            except PermissionError:
                if attempt < 2:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise
        return path  # pragma: no cover

    # Max lines of standards to inline in compact mode
    _MAX_INLINE_STANDARDS = 10

    def _build_common_body(
        self, ctx: AdapterContext, *, mode: str = "full"
    ) -> list[str]:
        """Build adapter body content.

        Modes:
            full    — AGENTS.md: complete Session Start + Workflow + Boundaries + Commands
            slim    — Tier 1 with AGENTS.md: one-line pointer
            compact — Tier 2: inline standards + compact rules, no "read files" instruction
        """
        lines: list[str] = []

        # State summary always injected first (all modes)
        if ctx.state_summary:
            lines += ctx.state_summary.splitlines() + [""]

        if mode == "slim":
            lines += [
                "See AGENTS.md for all project standards, workflow, and rules.",
                "",
            ]
            return lines

        if mode == "compact":
            # Tier 2: inline standards + compact rules — no file-read instructions
            if ctx.standards:
                # Extract complete rule blocks (- line + continuation lines)
                std_lines: list[str] = []
                rule_count = 0
                for raw_line in ctx.standards.splitlines():
                    stripped = raw_line.strip()
                    if stripped.startswith("- ") and stripped != "- (none)":
                        if rule_count >= self._MAX_INLINE_STANDARDS:
                            break
                        std_lines.append(stripped)
                        rule_count += 1
                    elif std_lines and (raw_line.startswith("  ") or raw_line.startswith("\t")):
                        # Continuation line (indented under a bullet)
                        std_lines.append(raw_line.rstrip())
                    # Skip non-bullet, non-continuation lines (headers, blanks)
                if std_lines:
                    lines += ["## Standards", ""]
                    lines += std_lines
                    lines += [""]

            lines += [
                "## Workflow",
                "",
                "Checkpoint: mark `[x]` in `state/tasks.md`, append progress"
                " to `state/current.md` (best-effort, git is ground truth).",
                "Reality-First: git > memory. Do NOT invent tasks.",
                "",
                "## Boundaries",
                "",
                "- Do NOT modify `.vibe/config.toml` or `.vibe/state/.lifecycle`",
                "- Do NOT run destructive commands without human confirmation",
                "",
                "## Vibe Commands (run in terminal, not code)",
                "",
                "`vibe init` | `vibe start` | `vibe sync` | `vibe status` | `vibe adapt`",
                "",
            ]
            return lines

        # mode == "full" — AGENTS.md: complete version
        lines += [
            "## Session Start — READ THESE FILES",
            "",
            "At the beginning of every session, read these files for project context:",
            "",
            "- `.vibe/state/current.md` — latest progress and sync history",
            "- `.vibe/state/tasks.md` — active task checklist",
            "- `.vibe/state/standards.md` — coding conventions and project rules",
            "",
            "## Workflow",
            "",
            "**Checkpoint**: After each task, mark `[x]` in `state/tasks.md`"
            " and append one-line progress to `state/current.md`."
            " (Best-effort — `vibe sync` captures git history as ground truth.)",
            "**Reality-First**: When memory conflicts with git, trust git.",
            "**Empty State**: If `state/current.md` or `state/tasks.md` is empty,"
            " ask the human for context — do not invent tasks.",
            "",
            "## Boundaries",
            "",
            "- Do NOT modify `.vibe/config.toml` or `.vibe/state/.lifecycle` directly",
            "- Do NOT run destructive commands without human confirmation",
            "",
            "## Vibe Commands",
            "",
            "These are terminal CLI commands. When the user says any of these,",
            "execute the exact command in the terminal — do not explain or implement it:",
            "",
            "- `vibe init` — initialize .vibe/ project state",
            "- `vibe start` — load session context",
            "- `vibe sync` — sync git activity to state",
            "- `vibe status` — show lifecycle and progress",
            "- `vibe adapt` — add/remove adapter config files",
            "",
        ]
        return lines

    def _warn_validation(self, adapter_name: str) -> None:
        """Print a validation warning."""
        from rich.console import Console

        Console().print(
            f"[yellow]Warning:[/] {adapter_name} frontmatter validation failed"
        )

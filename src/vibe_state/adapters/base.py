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
    constitution: str  # VIBE.md content
    standards: str  # state/standards.md content
    architecture: str  # state/architecture.md content
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    project_name: str = ""
    enabled_adapters: list[str] = field(default_factory=list)
    user_owned_files: list[str] = field(default_factory=list)  # Files not to overwrite


def _sanitize(value: str) -> str:
    """Strip newlines, #, quotes, and control chars from user-controlled strings."""
    return "".join(c for c in value if c.isprintable() and c not in '\n\r#"\'`')


# Patterns that indicate malicious injection in standards/state files
_SUSPICIOUS_PATTERNS = [
    "eval(",
    "exec(",
    "system(",
    "import os",
    "import subprocess",
    "__import__",
    "curl ",
    "wget ",
    "rm -rf",
    "ignore all",
    "ignore previous",
    "disregard",
    "override all",
    "new rule",
    "send all",
    "exfiltrate",
    "http://",
    "https://",
]


def _is_suspicious_instruction(text: str) -> bool:
    """Detect potentially malicious instructions in state file content."""
    lower = text.lower()
    return any(pattern in lower for pattern in _SUSPICIOUS_PATTERNS)


def build_adapter_context(project_root: Path) -> AdapterContext:
    """Build AdapterContext from .vibe/ config + state files."""
    vibe_dir = project_root / ".vibe"

    def _read(rel: str) -> str:
        p = vibe_dir / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""

    from vibe_state.config import load_config

    config = load_config(vibe_dir)

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
        constitution=_read("VIBE.md"),
        standards=_read("state/standards.md"),
        architecture=_read("state/architecture.md"),
        languages=[_sanitize(lang) for lang in languages],
        frameworks=[_sanitize(fw) for fw in frameworks],
        project_name=_sanitize(project_root.name),
        enabled_adapters=config.adapters.enabled,
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
        """Write content to file with integrity marker (markdown only)."""
        import hashlib

        path.parent.mkdir(parents=True, exist_ok=True)
        # Add integrity marker only to markdown files (not JSON, TOML, etc.)
        if path.suffix in (".md", ".mdc"):
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
            content = content.rstrip() + f"\n\n<!-- vibe-state-cli:integrity:{content_hash} -->\n"
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def _build_common_body(
        self, ctx: AdapterContext, *, slim: bool = False
    ) -> list[str]:
        """Build the common project info + standards + security block.

        Args:
            slim: If True, emit only the session-start directive (for when
                  AGENTS.md is also enabled and already carries the full body).
        """
        lines: list[str] = []

        if slim:
            # Minimal: just point to AGENTS.md and .vibe/ for details
            lines += [
                "See AGENTS.md for project standards and security rules.",
                "",
            ]
        else:
            if ctx.languages:
                lines.append(f"- Languages: {', '.join(ctx.languages)}")
            if ctx.frameworks:
                lines.append(f"- Frameworks: {', '.join(ctx.frameworks)}")

            # Pull standards with injection detection
            has_security = False
            if ctx.standards:
                for line in ctx.standards.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("- ") and not stripped.startswith("- ("):
                        lower = stripped.lower()
                        if _is_suspicious_instruction(lower):
                            continue
                        lines.append(_sanitize(stripped))
                        if "hardcode" in lower or "secret" in lower:
                            has_security = True

            # Only add security block if standards didn't already include it
            if not has_security:
                lines += [
                    "",
                    "## Security",
                    "",
                    "- Never hardcode secrets, tokens, or passwords",
                    "- Use .env files for environment variables",
                ]

        # Always include: session-start directive + boundaries
        lines += [
            "",
            "## Session Start — READ THESE FILES",
            "",
            "At the beginning of every session, read these files for project context:",
            "",
            "- `.vibe/state/current.md` — latest progress and sync history",
            "- `.vibe/state/tasks.md` — active task checklist",
            "- `.vibe/VIBE.md` — project constitution and workflow SOP",
            "",
            "## Boundaries",
            "",
            "- Do NOT modify `.vibe/config.toml` or `.vibe/state/.lifecycle` directly",
            "- Do NOT run destructive commands without human confirmation",
            "",
        ]
        return lines

    def _warn_validation(self, adapter_name: str) -> None:
        """Print a validation warning."""
        from rich.console import Console

        Console().print(
            f"[yellow]Warning:[/] {adapter_name} frontmatter validation failed"
        )

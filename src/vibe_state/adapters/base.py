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
                "## AutoResearch",
                "",
                "For measurable goals (coverage ↑, latency ↓, score ↑):",
                "`/autoresearch:plan` → `/autoresearch` → `vibe sync` (auto-tracks results)",
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
        ]
        lines += self._build_memory_section(ctx)
        lines += [
            "## Workflow",
            "",
            "**Checkpoint**: After each task, mark `[x]` in `state/tasks.md`"
            " and append one-line progress to `state/current.md`."
            " (Best-effort — `vibe sync` captures git history as ground truth.)",
            "**Reality-First**: When memory conflicts with git, trust git.",
            "**Empty State**: If `state/current.md` or `state/tasks.md` is empty,"
            " ask the human for context — do not invent tasks.",
            "",
            "## AutoResearch — Experiment Loop",
            "",
            "When facing a measurable optimization goal (coverage, performance,",
            "bundle size, score), suggest `/autoresearch` to the human.",
            "",
            "Closed loop:",
            "1. `/autoresearch:plan` — define Goal, Scope, Metric, Verify",
            "2. `/autoresearch` — run Modify → Verify → Keep/Discard → Repeat",
            "3. `vibe sync` — captures experiment commits to state/experiments.md",
            "4. `vibe start` — next session shows kept/reverted summary",
            "",
            "Key commands:",
            "- `/autoresearch` — main optimization loop",
            "- `/autoresearch:plan` — interactive setup wizard",
            "- `/autoresearch:debug` — scientific bug hunting",
            "- `/autoresearch:fix` — auto-repair until zero errors",
            "- `/autoresearch:security` — STRIDE + OWASP audit",
            "",
            "Results are tracked in `.vibe/state/experiments.md` automatically.",
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

    def _build_memory_section(self, ctx: AdapterContext) -> list[str]:
        """v0.3.7: BM-aware persistent knowledge section for full-mode
        AGENTS.md.

        Driven by `[memory]` config in .vibe/config.toml:
        - enabled=False → empty list (section completely skipped)
        - enabled=True + projects=[]  → generic "query whichever projects
          you find" instruction (the SAFE default that never leaks
          owner-specific project names)
        - enabled=True + projects=[…] → explicit project list rendered
          into the template

        Mechanism is vendor-neutral via `target` string. Today's known
        value is `basic-memory`; future targets (obsidian, logseq, ...)
        get their own branch below.
        """
        try:
            from vibe_state.config import load_config

            config = load_config(ctx.vibe_dir)
            mem = config.memory
        except Exception:
            # Config not readable (fresh init mid-render etc.) — skip
            # the section rather than fail the whole adapter emit.
            return []

        if not mem.enabled:
            return []

        if mem.target == "basic-memory":
            return self._build_basic_memory_section(mem.projects)

        # Unknown target — render a minimal vendor-agnostic stub so the
        # user is told something is configured but the template doesn't
        # claim to know how to query it.
        return [
            "## Persistent Knowledge — QUERY BEFORE RECALL",
            "",
            f"A persistent knowledge layer (`target = \"{mem.target}\"`) is"
            " configured for this project. Before answering recall questions",
            "(\"what did we decide\", \"where did we leave off\"), query it"
            " using whatever interface your agent supports.",
            "",
            "If the layer is unreachable (offline / not configured on this"
            " machine), proceed without it and note the gap.",
            "",
        ]

    @staticmethod
    def _build_basic_memory_section(projects: list[str]) -> list[str]:
        """Render the Basic Memory variant of the persistent-knowledge
        section. Separated from `_build_memory_section` so future targets
        get their own pure renderer without entangling with the
        config-loading code path."""
        lines = [
            "## Persistent Knowledge — QUERY BEFORE RECALL",
            "",
            "This project's persistent cross-machine knowledge lives in"
            " **Basic Memory** (markdown-on-disk knowledge graph,"
            " MCP-accessible from any agent).",
            "",
            "Before answering recall questions"
            " (\"what did we decide\", \"where did we leave off\","
            " \"what's our principle on X\"), query the knowledge layer"
            " first:",
            "",
            "- `mcp__basic-memory__search_notes(query=\"…\")` — text + semantic search",
            "- `mcp__basic-memory__search_notes(metadata_filters={\"type\":"
            " \"decision\"})` — structured query by type",
            "- `mcp__basic-memory__build_context(url=\"memory://<topic>\","
            " depth=2)` — graph traversal from a seed note",
            "",
        ]
        if projects:
            lines.append("Projects to read (in order):")
            for p in projects:
                lines.append(f"- `{p}`")
        else:
            # Generic default — never leaks owner-specific project names.
            # Agent uses whatever projects it can discover.
            lines += [
                "Projects: query whichever Basic Memory projects this"
                " agent has access to (use `mcp__basic-memory__list_memory_projects`"
                " to enumerate). Configure preferred projects in"
                " `.vibe/config.toml` under `[memory].projects = [...]`.",
            ]
        lines += [
            "",
            "**Fallback**: If Basic Memory is offline, the MCP server is"
            " not registered, or a query fails/times out, fall back to"
            " `.vibe/state/` files (current.md, tasks.md, standards.md)"
            " as your baseline — they are the on-disk ground truth this"
            " repo always carries. Print a one-line warning to the human"
            " (e.g. `⚠ Basic Memory unavailable — using .vibe/state only`),"
            " do NOT retry MCP calls, do NOT block on the recall.",
            "",
            "**Performance**: First Basic Memory call may be slow if the"
            " daemon is cold-starting (≥30s on Windows). Use short"
            " per-query timeouts (~5s); treat slow queries as unavailable"
            " rather than waiting.",
            "",
            "Capture material decisions as notes with `type: decision`"
            " to keep the layer fresh.",
            "",
        ]
        return lines

    def _warn_validation(self, adapter_name: str) -> None:
        """Print a validation warning."""
        from rich.console import Console

        Console().print(
            f"[yellow]Warning:[/] {adapter_name} frontmatter validation failed"
        )

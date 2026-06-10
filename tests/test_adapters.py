"""All 8 adapters: registry, detect/emit/clean/validate, three-mode output
(full/slim/compact), state summary injection, skills, build_context."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from vibe_state.adapters.base import (
    AdapterContext,
    _sanitize,
)
from vibe_state.adapters.registry import (
    detect_tools,
    get_adapter,
    get_all_adapter_names,
    get_all_adapters,
)
from vibe_state.config import VibeConfig, save_config

# ── Helpers ──


def _make_ctx(tmp_path: Path, **kw: object) -> AdapterContext:
    vibe_dir = tmp_path / ".vibe"
    vibe_dir.mkdir(exist_ok=True)
    (vibe_dir / "state").mkdir(exist_ok=True)
    (vibe_dir / "state" / "standards.md").write_text(
        "# Standards\n\n- Use snake_case\n- Write tests\n", encoding="utf-8"
    )
    defaults = dict(
        project_root=tmp_path,
        vibe_dir=vibe_dir,

        standards="# Standards\n\n- Use snake_case\n- Write tests\n",
        architecture="# Architecture\n| Language | Python | - |\n",
        languages=["Python"],
        frameworks=["FastAPI"],
        project_name="test-project",
        enabled_adapters=["agents_md", "claude"],
    )
    defaults.update(kw)
    return AdapterContext(**defaults)


def _slim_ctx(tmp_path: Path, **kw: object) -> AdapterContext:
    vibe = tmp_path / ".vibe"
    vibe.mkdir(exist_ok=True)
    (vibe / "state").mkdir(exist_ok=True)
    defaults = dict(
        project_root=tmp_path, vibe_dir=vibe,
        standards="- Use snake_case\n",
        architecture="", languages=["Python"], frameworks=[],
        project_name="test", enabled_adapters=["agents_md"],
    )
    defaults.update(kw)
    return AdapterContext(**defaults)


def _files_content(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── Registry ──


class TestAdapterRegistry:
    def test_all_adapters_registered(self) -> None:
        names = get_all_adapter_names()
        expected = {
            "agents_md", "antigravity", "claude", "cursor",
            "copilot", "windsurf", "cline", "roo",
        }
        assert expected == set(names)

    def test_get_unknown_adapter_returns_none(self) -> None:
        assert get_adapter("nonexistent") is None

    def test_get_all_adapters_returns_instances(self) -> None:
        adapters = get_all_adapters()
        assert len(adapters) == 8
        for _name, adapter in adapters.items():
            assert hasattr(adapter, "emit")

    def test_detect_tools_finds_claude(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        detected = detect_tools(tmp_path)
        assert "claude" in detected

    def test_detect_tools_empty(self, tmp_path: Path) -> None:
        detected = detect_tools(tmp_path)
        assert detected == []


# ── AGENTS.md Adapter ──


class TestAgentsMdAdapter:
    def test_emit_creates_file(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 1
        assert files[0].name == "AGENTS.md"
        assert files[0].exists()

    def test_content_includes_bootstrap(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "test-project" in content
        assert "state/standards.md" in content  # Points to standards, doesn't copy
        assert "state/current.md" in content
        assert "## Vibe Commands" in content

    def test_validate_size_limit(self) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        assert adapter.validate("short content")
        assert not adapter.validate("x" * (33 * 1024))

    def test_detect(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        assert not adapter.detect(tmp_path)
        (tmp_path / "AGENTS.md").write_text("test", encoding="utf-8")
        assert adapter.detect(tmp_path)

    def test_clean(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        (tmp_path / "AGENTS.md").write_text("test", encoding="utf-8")
        files = adapter.clean(tmp_path)
        assert len(files) == 1

    def test_oversize_triggers_warn(self, tmp_path: Path) -> None:
        a = get_adapter("agents_md")
        assert a is not None
        big = "- " + "x" * 40000 + "\n"
        ctx = _make_ctx(tmp_path, standards=big)
        files = a.emit(ctx)  # Should print warning but not crash
        assert len(files) == 1

    def test_warn_oversize_validate(self, tmp_path: Path) -> None:
        a = get_adapter("agents_md")
        assert a is not None
        assert not a.validate("x" * 33000)


# ── Claude Adapter ──


class TestClaudeAdapter:
    def test_emit_creates_files(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert any(f.name == "CLAUDE.md" for f in files)
        assert any("vibe-standards.md" in f.name for f in files)

    def test_imports_agents_md_when_both_enabled(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        ctx.enabled_adapters = ["agents_md", "claude"]
        adapter.emit(ctx)
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "@AGENTS.md" in content

    def test_self_contained_when_alone(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        ctx.enabled_adapters = ["claude"]
        adapter.emit(ctx)
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "@AGENTS.md" not in content
        assert "state/standards.md" in content  # Bootstrap: points to standards

    def test_rules_have_paths_frontmatter(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        rules_path = tmp_path / ".claude" / "rules" / "vibe-standards.md"
        content = rules_path.read_text(encoding="utf-8")
        assert "paths:" in content

    def test_detect_via_file(self, tmp_path: Path) -> None:
        a = get_adapter("claude")
        assert a is not None
        (tmp_path / "CLAUDE.md").write_text("x")
        assert a.detect(tmp_path)

    def test_emit_creates_skills(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        skill_files = [f for f in files if f.name == "SKILL.md"]
        assert len(skill_files) == 5
        expected = {"vibe-init", "vibe-start", "vibe-sync", "vibe-status", "vibe-adapt"}
        actual = {f.parent.name for f in skill_files}
        assert actual == expected

    def test_skill_content_format(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        skill = tmp_path / ".claude" / "skills" / "vibe-sync" / "SKILL.md"
        content = skill.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "name: vibe-sync" in content
        assert "description:" in content
        assert "vibe sync" in content

    def test_clean_includes_skills(self, tmp_path: Path) -> None:
        a = get_adapter("claude")
        assert a is not None
        ctx = _slim_ctx(tmp_path, enabled_adapters=["claude"])
        a.emit(ctx)
        files = a.clean(tmp_path)
        skill_files = [f for f in files if f.name == "SKILL.md"]
        assert len(skill_files) == 5


# ── Vibe Commands in common body ──


class TestVibeCommandsSection:
    def test_vibe_commands_in_agents_md(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path, enabled_adapters=["agents_md"])
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "## Vibe Commands" in content
        assert "vibe init" in content
        assert "vibe sync" in content
        assert "execute the exact command in the terminal" in content

    def test_slim_mode_only_pointer(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path, enabled_adapters=["agents_md", "claude"])
        adapter.emit(ctx)
        rules = (tmp_path / ".claude" / "rules" / "vibe-standards.md").read_text(encoding="utf-8")
        assert "See AGENTS.md" in rules
        assert "## Vibe Commands" not in rules  # Slim = no duplication


# ── State summary injection ──


class TestStateSummaryInjection:
    def test_summary_in_agents_md(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path, state_summary="## Last Session\n\n- Progress: test\n")
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "## Last Session" in content
        assert "Progress: test" in content

    def test_no_summary_when_empty(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path, state_summary="")
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "## Last Session" not in content

    def test_summary_in_slim_mode(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(
            tmp_path,
            enabled_adapters=["agents_md", "claude"],
            state_summary="## Last Session\n\n- Progress: slim test\n",
        )
        adapter.emit(ctx)
        rules = (tmp_path / ".claude" / "rules" / "vibe-standards.md").read_text(encoding="utf-8")
        assert "Progress: slim test" in rules
        assert "See AGENTS.md" in rules


# ── Compact mode output ──


class TestCompactMode:
    """v0.3.6: compact-mode adapters (cursor/cline/windsurf/roo/copilot)
    now shim to AGENTS.md when it's co-enabled. They only inline
    standards/workflow when AGENTS.md is NOT enabled (standalone fallback).
    """

    def test_compact_inlines_standards_when_standalone(
        self, tmp_path: Path
    ) -> None:
        """When AGENTS.md is NOT co-enabled, cursor must still be a
        self-contained config — inline standards, no broken references."""
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(
            tmp_path,
            standards="- Use snake_case\n- Write tests\n",
            enabled_adapters=["cursor"],
        )
        adapter.emit(ctx)
        mdc = tmp_path / ".cursor" / "rules" / "vibe-standards.mdc"
        content = mdc.read_text(encoding="utf-8")
        assert "snake_case" in content  # Standards inlined
        assert "READ THESE FILES" not in content  # No file-read instruction
        assert "See AGENTS.md" not in content  # No broken shim

    def test_shims_to_agents_md_when_co_enabled(
        self, tmp_path: Path
    ) -> None:
        """v0.3.6 pivot: when AGENTS.md is co-enabled (the common case),
        cursor emits a one-line shim — single source of truth, less drift."""
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(
            tmp_path,
            standards="- Use snake_case\n- Write tests\n",
            enabled_adapters=["agents_md", "cursor"],
        )
        adapter.emit(ctx)
        mdc = tmp_path / ".cursor" / "rules" / "vibe-standards.mdc"
        content = mdc.read_text(encoding="utf-8")
        assert "See AGENTS.md" in content
        # Standards must NOT be duplicated — that's the whole point
        assert "snake_case" not in content

    def test_compact_has_workflow_and_commands_when_standalone(
        self, tmp_path: Path
    ) -> None:
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(tmp_path, enabled_adapters=["cursor"])
        adapter.emit(ctx)
        mdc = tmp_path / ".cursor" / "rules" / "vibe-standards.mdc"
        content = mdc.read_text(encoding="utf-8")
        assert "## Workflow" in content
        assert "## Boundaries" in content
        assert "Vibe Commands" in content
        assert "vibe sync" in content

    def test_compact_limits_standards_to_10_when_standalone(
        self, tmp_path: Path
    ) -> None:
        """Compact mode should only inline first 10 standard lines."""
        many_rules = "\n".join(f"- Rule {i}" for i in range(20))
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(
            tmp_path,
            standards=many_rules,
            enabled_adapters=["cursor"],
        )
        adapter.emit(ctx)
        mdc = tmp_path / ".cursor" / "rules" / "vibe-standards.mdc"
        content = mdc.read_text(encoding="utf-8")
        assert "Rule 9" in content
        assert "Rule 10" not in content  # 11th rule (0-indexed)

    def test_all_compact_adapters_shim_when_agents_md_co_enabled(
        self, tmp_path: Path
    ) -> None:
        """v0.3.6 contract: all five compact-mode adapters honor the shim
        pivot when AGENTS.md is co-enabled. Regression net for the whole
        family.
        """
        adapters_paths = [
            ("cursor", tmp_path / ".cursor" / "rules" / "vibe-standards.mdc"),
            ("cline", tmp_path / ".clinerules" / "01-vibe-standards.md"),
            ("windsurf", tmp_path / ".windsurf" / "rules" / "vibe-standards.md"),
            ("roo", tmp_path / ".roo" / "rules" / "01-vibe-standards.md"),
            ("copilot", tmp_path / ".github" / "copilot-instructions.md"),
        ]
        for name, path in adapters_paths:
            adapter = get_adapter(name)
            assert adapter is not None
            ctx = _make_ctx(
                tmp_path,
                standards="- Use snake_case\n",
                enabled_adapters=["agents_md", name],
            )
            adapter.emit(ctx)
            content = path.read_text(encoding="utf-8")
            assert "See AGENTS.md" in content, f"{name} did not shim"
            assert "snake_case" not in content, (
                f"{name} duplicated standards instead of shimming"
            )


# ── Adapters always generate fresh (legacy archived by init) ──


class TestAdaptersAlwaysGenerate:
    def test_claude_generates_even_with_existing(self, tmp_path: Path) -> None:
        """Claude adapter always generates CLAUDE.md (init archives old one)."""
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert any(f.name == "CLAUDE.md" for f in files)
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "vibe-state-cli:managed" in content

    def test_agents_md_generates_fresh(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path, enabled_adapters=["agents_md"])
        files = adapter.emit(ctx)
        assert len(files) == 1
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "vibe-state-cli:managed" in content
        assert "## Vibe Commands" in content


# ── Cursor Adapter ──


class TestCursorAdapter:
    def test_emit_creates_mdc(self, tmp_path: Path) -> None:
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 1
        assert files[0].suffix == ".mdc"

    def test_valid_frontmatter(self, tmp_path: Path) -> None:
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = _files_content(tmp_path / ".cursor" / "rules" / "vibe-standards.mdc")
        assert adapter.validate(content)

    def test_invalid_frontmatter(self) -> None:
        adapter = get_adapter("cursor")
        assert adapter is not None
        assert not adapter.validate("no frontmatter here")
        assert not adapter.validate("---\nfoo: bar\n---\ncontent")

    def test_detect(self, tmp_path: Path) -> None:
        adapter = get_adapter("cursor")
        assert adapter is not None
        assert not adapter.detect(tmp_path)
        (tmp_path / ".cursor").mkdir()
        assert adapter.detect(tmp_path)

    def test_clean(self, tmp_path: Path) -> None:
        a = get_adapter("cursor")
        assert a is not None
        ctx = _slim_ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) == 1

    def test_missing_description(self) -> None:
        a = get_adapter("cursor")
        assert a is not None
        assert not a.validate("---\nalwaysApply: true\n---\n")


# ── Copilot Adapter ──


class TestCopilotAdapter:
    def test_emit_creates_files(self, tmp_path: Path) -> None:
        adapter = get_adapter("copilot")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 2
        assert any("copilot-instructions.md" in f.name for f in files)
        assert any("vibe-standards.instructions.md" in f.name for f in files)

    def test_scoped_has_applyto(self, tmp_path: Path) -> None:
        adapter = get_adapter("copilot")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        scoped = tmp_path / ".github" / "instructions" / "vibe-standards.instructions.md"
        content = scoped.read_text(encoding="utf-8")
        assert "applyTo" in content

    def test_detect(self, tmp_path: Path) -> None:
        a = get_adapter("copilot")
        assert a is not None
        assert not a.detect(tmp_path)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text("x")
        assert a.detect(tmp_path)

    def test_clean(self, tmp_path: Path) -> None:
        a = get_adapter("copilot")
        assert a is not None
        ctx = _slim_ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) >= 1

    def test_validate_main(self) -> None:
        a = get_adapter("copilot")
        assert a is not None
        assert a.validate("# No frontmatter\nContent")
        assert a.validate("---\napplyTo: '**/*'\n---\nContent")

    def test_scoped_invalid(self) -> None:
        a = get_adapter("copilot")
        assert a is not None
        assert not a.validate("---\nwrongField: true\n---\n")


# ── Windsurf Adapter ──


class TestWindsurfAdapter:
    def test_emit_and_validate(self, tmp_path: Path) -> None:
        adapter = get_adapter("windsurf")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert adapter.validate(content)
        assert "trigger: always_on" in content

    def test_invalid_trigger(self) -> None:
        adapter = get_adapter("windsurf")
        assert adapter is not None
        assert not adapter.validate("---\ntrigger: invalid_value\ndescription: test\n---\n")

    def test_detect(self, tmp_path: Path) -> None:
        a = get_adapter("windsurf")
        assert a is not None
        assert not a.detect(tmp_path)
        (tmp_path / ".windsurf").mkdir()
        assert a.detect(tmp_path)

    def test_clean(self, tmp_path: Path) -> None:
        a = get_adapter("windsurf")
        assert a is not None
        ctx = _slim_ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) == 1

    def test_validate_details(self) -> None:
        a = get_adapter("windsurf")
        assert a is not None
        assert not a.validate("no frontmatter")
        assert not a.validate("---\ntrigger: always_on\n---\n")  # no description
        assert a.validate("---\ntrigger: always_on\ndescription: test\n---\n")

    def test_missing_description(self) -> None:
        a = get_adapter("windsurf")
        assert a is not None
        assert not a.validate("---\ntrigger: always_on\n---\n")


# ── Cline Adapter ──


class TestClineAdapter:
    def test_emit_and_validate(self, tmp_path: Path) -> None:
        adapter = get_adapter("cline")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert adapter.validate(content)
        assert "paths:" in content

    def test_detect(self, tmp_path: Path) -> None:
        adapter = get_adapter("cline")
        assert adapter is not None
        assert not adapter.detect(tmp_path)
        (tmp_path / ".clinerules").mkdir()
        assert adapter.detect(tmp_path)

    def test_clean(self, tmp_path: Path) -> None:
        a = get_adapter("cline")
        assert a is not None
        ctx = _slim_ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) == 1

    def test_validate_no_frontmatter(self) -> None:
        a = get_adapter("cline")
        assert a is not None
        assert not a.validate("no frontmatter")

    def test_invalid_emits_warn(self, tmp_path: Path) -> None:
        """Cline: frontmatter missing paths -> validation warn."""
        a = get_adapter("cline")
        assert a is not None
        assert not a.validate("---\nfoo: bar\n---\n")
        assert a.validate("---\npaths:\n  - '**/*'\n---\n")


# ── Roo Code Adapter ──


class TestRooAdapter:
    def test_emit_no_frontmatter(self, tmp_path: Path) -> None:
        adapter = get_adapter("roo")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert not content.startswith("---")
        assert "Vibe Standards" in content

    def test_detect(self, tmp_path: Path) -> None:
        a = get_adapter("roo")
        assert a is not None
        assert not a.detect(tmp_path)
        (tmp_path / ".roo").mkdir()
        assert a.detect(tmp_path)

    def test_clean(self, tmp_path: Path) -> None:
        a = get_adapter("roo")
        assert a is not None
        ctx = _slim_ctx(tmp_path)
        a.emit(ctx)
        files = a.clean(tmp_path)
        assert len(files) == 1

    def test_default_validate_returns_true(self) -> None:
        a = get_adapter("roo")
        assert a is not None
        assert a.validate("anything") is True


# ── Antigravity Adapter ──


class TestAntigravityAdapter:
    def test_emit_creates_gemini_md_and_agents_skills(
        self, tmp_path: Path
    ) -> None:
        """v0.3.6 transition: adapter writes BOTH the legacy GEMINI.md
        (deprecated, removed after 2026-06-18) AND the new Antigravity CLI
        layout (.agents/skills/*/SKILL.md)."""
        adapter = get_adapter("antigravity")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        names = {f.name for f in files}
        assert "GEMINI.md" in names
        assert "SKILL.md" in names
        # 5 skills + 1 GEMINI.md
        assert len(files) == 6
        for skill_name in (
            "vibe-init", "vibe-start", "vibe-sync", "vibe-status", "vibe-adapt"
        ):
            assert (tmp_path / ".agents" / "skills" / skill_name / "SKILL.md").exists()

    def test_gemini_md_carries_deprecation_banner(self, tmp_path: Path) -> None:
        adapter = get_adapter("antigravity")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")
        assert "deprecated" in content.lower()
        assert "2026-06-18" in content
        assert "Antigravity CLI" in content

    def test_imports_agents_md_when_both_enabled(self, tmp_path: Path) -> None:
        adapter = get_adapter("antigravity")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        ctx.enabled_adapters = ["agents_md", "antigravity"]
        adapter.emit(ctx)
        content = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")
        assert "@AGENTS.md" in content

    def test_self_contained_when_alone(self, tmp_path: Path) -> None:
        adapter = get_adapter("antigravity")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        ctx.enabled_adapters = ["antigravity"]
        adapter.emit(ctx)
        content = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")
        assert "@AGENTS.md" not in content
        assert "snake_case" in content  # Standards inlined in compact mode

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        adapter = get_adapter("antigravity")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")
        assert not content.startswith("---")

    def test_detect(self, tmp_path: Path) -> None:
        adapter = get_adapter("antigravity")
        assert adapter is not None
        assert not adapter.detect(tmp_path)
        (tmp_path / "GEMINI.md").write_text("test", encoding="utf-8")
        assert adapter.detect(tmp_path)

    def test_detect_via_agents_dir(self, tmp_path: Path) -> None:
        """v0.3.6: adapter should also detect projects already using the
        new .agents/ layout, not just legacy GEMINI.md."""
        adapter = get_adapter("antigravity")
        assert adapter is not None
        (tmp_path / ".agents").mkdir()
        assert adapter.detect(tmp_path)

    def test_clean_covers_both_layouts(self, tmp_path: Path) -> None:
        a = get_adapter("antigravity")
        assert a is not None
        ctx = _slim_ctx(tmp_path)
        a.emit(ctx)
        cleaned = a.clean(tmp_path)
        assert tmp_path / "GEMINI.md" in cleaned
        for skill_name in (
            "vibe-init", "vibe-start", "vibe-sync", "vibe-status", "vibe-adapt"
        ):
            assert (
                tmp_path / ".agents" / "skills" / skill_name / "SKILL.md"
                in cleaned
            )


# ── Validate-fail warn paths (patched validate) ──


class TestAdapterValidateFailPaths:
    def test_cline_warn_on_bad_validate(self, tmp_path: Path) -> None:
        a = get_adapter("cline")
        assert a is not None
        with patch.object(a, "validate", return_value=False):
            files = a.emit(_slim_ctx(tmp_path))
            assert len(files) == 1

    def test_copilot_warn_on_bad_validate(self, tmp_path: Path) -> None:
        a = get_adapter("copilot")
        assert a is not None
        with patch.object(a, "validate", return_value=False):
            files = a.emit(_slim_ctx(tmp_path))
            assert len(files) == 2

    def test_cursor_warn_on_bad_validate(self, tmp_path: Path) -> None:
        a = get_adapter("cursor")
        assert a is not None
        with patch.object(a, "validate", return_value=False):
            files = a.emit(_slim_ctx(tmp_path))
            assert len(files) == 1

    def test_windsurf_warn_on_bad_validate(self, tmp_path: Path) -> None:
        a = get_adapter("windsurf")
        assert a is not None
        with patch.object(a, "validate", return_value=False):
            files = a.emit(_slim_ctx(tmp_path))
            assert len(files) == 1


# ── Warn validation ──


class TestAdapterWarnValidation:
    def test_warn_validation_prints(self, tmp_path: Path) -> None:
        a = get_adapter("cursor")
        assert a is not None
        a._warn_validation("test-adapter")
        # No crash = pass


# ── Standards inclusion ──


class TestAdapterBootstrapMode:
    def test_adapter_points_to_standards_not_copies(self, tmp_path: Path) -> None:
        """Adapter output should reference state/standards.md, not embed its content."""
        a = get_adapter("agents_md")
        assert a is not None
        ctx = _make_ctx(tmp_path, standards="- use snake_case\n- Write tests\n")
        files = a.emit(ctx)
        content = files[0].read_text(encoding="utf-8")
        assert "state/standards.md" in content  # Points to file
        assert "snake_case" not in content       # Doesn't copy content


# ── Build adapter context ──


class TestBuildAdapterContext:
    def test_parses_framework_from_architecture(self, tmp_path: Path) -> None:
        from vibe_state.adapters.base import build_adapter_context

        vibe = tmp_path / ".vibe"
        (vibe / "state").mkdir(parents=True)
        (vibe / "config.toml").write_text("[vibe]\nversion = 1\n")
        (vibe / "state" / "architecture.md").write_text(
            "# Arch\n- Language: Python\n- Framework: FastAPI\n"
        )
        (vibe / "state" / "standards.md").write_text("")
        ctx = build_adapter_context(tmp_path)
        assert "FastAPI" in ctx.frameworks


# ── Sanitize ──


class TestSanitize:
    def test_strips_newlines(self) -> None:
        assert _sanitize("hello\nworld") == "helloworld"

    def test_preserves_normal_text(self) -> None:
        assert _sanitize("Python 3.12") == "Python 3.12"

    def test_preserves_hash_and_quotes(self) -> None:
        assert _sanitize('## "hello" `code`') == '## "hello" `code`'


# ── v0.3.7: AGENTS.md BM-aware Session Start Protocol ──


def _write_config(vibe_dir: Path, **memory_overrides: object) -> None:
    """Write a config.toml with memory section overrides for tests."""
    config = VibeConfig()
    for k, v in memory_overrides.items():
        setattr(config.memory, k, v)
    save_config(vibe_dir, config)


class TestMemorySectionInjection:
    """v0.3.7: agents_md full-mode template gains a vendor-neutral
    persistent-knowledge section. Mechanism is config-driven; default
    is enabled with `target = "basic-memory"` and `projects = []`.
    """

    def test_default_config_injects_basic_memory_section(
        self, tmp_path: Path
    ) -> None:
        """Default config (enabled=True, target=basic-memory, projects=[])
        renders the canonical BM section."""
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        # No config file written → load_config returns defaults
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "## Persistent Knowledge — QUERY BEFORE RECALL" in content
        assert "Basic Memory" in content
        assert "mcp__basic-memory__search_notes" in content
        # Default projects=[] → generic instruction, not specific names
        assert "query whichever Basic Memory projects" in content

    def test_explicit_projects_listed_when_configured(
        self, tmp_path: Path
    ) -> None:
        """When the user configures specific projects, the template
        renders them as a list."""
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        _write_config(ctx.vibe_dir, projects=["work", "personal"])
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "- `work`" in content
        assert "- `personal`" in content
        # When explicit list is given, generic fallback text drops
        assert "query whichever Basic Memory projects" not in content

    def test_default_projects_never_leaks_owner_specific_names(
        self, tmp_path: Path
    ) -> None:
        """OSS safety net: the default project list must not contain
        any names from the maintainer's personal Basic Memory setup.
        Without this guard, a user pip-installing the package would see
        the maintainer's `personal` / `methodology` project names in
        their auto-generated AGENTS.md."""
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        # Specific BM project names the maintainer happens to use must
        # NOT appear as project bullets in the default output.
        assert "- `personal`" not in content
        assert "- `methodology`" not in content

    def test_disabled_skips_section_entirely(self, tmp_path: Path) -> None:
        """enabled=False means the section is completely absent —
        AGENTS.md regenerates as if v0.3.7 never added it."""
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        _write_config(ctx.vibe_dir, enabled=False)
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Persistent Knowledge" not in content
        assert "Basic Memory" not in content
        assert "mcp__basic-memory__" not in content
        # Workflow section still present (rest of template intact)
        assert "## Workflow" in content

    def test_unknown_target_renders_vendor_agnostic_stub(
        self, tmp_path: Path
    ) -> None:
        """Future-proofing: if user sets `target = "obsidian"` (or any
        other future target), the template emits a generic
        vendor-agnostic stub instead of breaking or leaking BM specifics."""
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        _write_config(ctx.vibe_dir, target="obsidian")
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "## Persistent Knowledge — QUERY BEFORE RECALL" in content
        assert 'target = "obsidian"' in content
        # BM-specific instructions must NOT leak when target is something else
        assert "mcp__basic-memory__" not in content
        assert "Basic Memory" not in content

    def test_offline_fallback_instruction_present(
        self, tmp_path: Path
    ) -> None:
        """The template must explicitly tell the agent what to do when
        the knowledge store is unreachable — silent failure is the worst
        case (agent stuck or wastes context guessing).

        v0.3.7 adversarial review tightened the fallback prose to:
        (a) name a concrete baseline (.vibe/state/ files),
        (b) cap retry behavior (do NOT retry, do NOT block),
        (c) specify how to surface the gap (one-line warning).
        """
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "**Fallback**" in content
        # Baseline must be named explicitly (not just "without it")
        assert ".vibe/state/" in content
        # Retry policy must be prescriptive
        assert "do NOT retry" in content or "do not retry" in content.lower()
        assert "do NOT block" in content or "do not block" in content.lower()
        # Cold-start performance caveat must surface (the original RFC
        # was filed BECAUSE of this exact 30s timeout problem)
        assert "Performance" in content
        assert "cold-start" in content.lower()

    def test_freshness_marker_preserved(self, tmp_path: Path) -> None:
        """The managed marker that vibe status uses for freshness
        detection must still be at the end of the file after the new
        section is added."""
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "<!-- vibe-state-cli:managed -->" in content
        # Marker should be near the end, after the new section
        marker_pos = content.rfind("<!-- vibe-state-cli:managed -->")
        section_pos = content.find("## Persistent Knowledge")
        assert marker_pos > section_pos, (
            "marker should come AFTER the memory section, not before"
        )

    def test_idempotent_regeneration(self, tmp_path: Path) -> None:
        """Running emit twice should produce byte-identical output —
        no drift, no accidental duplicate sections."""
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        first = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        adapter.emit(ctx)
        second = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert first == second
        # And only one section, not two
        assert first.count("## Persistent Knowledge") == 1

    def test_section_only_in_full_mode_not_slim_or_compact(
        self, tmp_path: Path
    ) -> None:
        """Memory section is the AGENTS.md baseline — it belongs in
        full mode only. Slim mode shims to AGENTS.md (inherits
        automatically). Compact mode is for tools without MCP, so the
        section would be useless there."""
        # Slim mode: claude.py rules file when AGENTS.md is co-enabled
        claude = get_adapter("claude")
        assert claude is not None
        ctx_with_agents = _make_ctx(tmp_path, enabled_adapters=["agents_md", "claude"])
        claude.emit(ctx_with_agents)
        rules = (tmp_path / ".claude" / "rules" / "vibe-standards.md").read_text(
            encoding="utf-8"
        )
        assert "## Persistent Knowledge" not in rules
        assert "See AGENTS.md" in rules

        # Compact mode: cursor when agents_md is NOT enabled
        # Use a fresh tmp_path to avoid file collision
        cursor_tmp = tmp_path / "cursor_only"
        cursor_tmp.mkdir()
        cursor_ctx = _make_ctx(
            cursor_tmp,
            enabled_adapters=["cursor"],
        )
        cursor = get_adapter("cursor")
        assert cursor is not None
        cursor.emit(cursor_ctx)
        mdc = (
            cursor_tmp / ".cursor" / "rules" / "vibe-standards.mdc"
        ).read_text(encoding="utf-8")
        assert "## Persistent Knowledge" not in mdc

    def test_section_inserted_between_session_start_and_workflow(
        self, tmp_path: Path
    ) -> None:
        """The section's position matters for human readability: it
        should appear between 'Session Start — READ THESE FILES' and
        '## Workflow', not after Boundaries or somewhere random."""
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        session_pos = content.find("## Session Start")
        memory_pos = content.find("## Persistent Knowledge")
        workflow_pos = content.find("## Workflow")
        assert session_pos < memory_pos < workflow_pos



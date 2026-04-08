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
    def test_compact_inlines_standards(self, tmp_path: Path) -> None:
        """Compact mode should inline standards directly, not point to file."""
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(tmp_path, standards="- Use snake_case\n- Write tests\n")
        adapter.emit(ctx)
        mdc = tmp_path / ".cursor" / "rules" / "vibe-standards.mdc"
        content = mdc.read_text(encoding="utf-8")
        assert "snake_case" in content  # Standards inlined
        assert "READ THESE FILES" not in content  # No file-read instruction

    def test_compact_has_workflow_and_commands(self, tmp_path: Path) -> None:
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        mdc = tmp_path / ".cursor" / "rules" / "vibe-standards.mdc"
        content = mdc.read_text(encoding="utf-8")
        assert "## Workflow" in content
        assert "## Boundaries" in content
        assert "Vibe Commands" in content
        assert "vibe sync" in content

    def test_compact_limits_standards_to_10(self, tmp_path: Path) -> None:
        """Compact mode should only inline first 10 standard lines."""
        many_rules = "\n".join(f"- Rule {i}" for i in range(20))
        adapter = get_adapter("cursor")
        assert adapter is not None
        ctx = _make_ctx(tmp_path, standards=many_rules)
        adapter.emit(ctx)
        mdc = tmp_path / ".cursor" / "rules" / "vibe-standards.mdc"
        content = mdc.read_text(encoding="utf-8")
        assert "Rule 9" in content
        assert "Rule 10" not in content  # 11th rule (0-indexed)


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
    def test_emit_creates_gemini_md(self, tmp_path: Path) -> None:
        adapter = get_adapter("antigravity")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 1
        assert files[0].name == "GEMINI.md"

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

    def test_clean(self, tmp_path: Path) -> None:
        a = get_adapter("antigravity")
        assert a is not None
        ctx = _slim_ctx(tmp_path)
        a.emit(ctx)
        assert a.clean(tmp_path) == [tmp_path / "GEMINI.md"]


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



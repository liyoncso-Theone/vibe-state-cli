"""Tests for all adapter implementations."""

from __future__ import annotations

from pathlib import Path

from vibe_state.adapters.base import AdapterContext
from vibe_state.adapters.registry import get_adapter, get_all_adapter_names

# ── Registry ──


def test_all_adapters_registered() -> None:
    names = get_all_adapter_names()
    expected = {
        "agents_md", "antigravity", "claude", "cursor",
        "copilot", "windsurf", "cline", "roo",
    }
    assert expected == set(names)


def test_get_unknown_adapter() -> None:
    assert get_adapter("nonexistent") is None


# ── Helpers ──


def _make_ctx(tmp_path: Path) -> AdapterContext:
    vibe_dir = tmp_path / ".vibe"
    vibe_dir.mkdir()
    (vibe_dir / "state").mkdir()
    (vibe_dir / "state" / "standards.md").write_text(
        "# Standards\n\n- Use snake_case\n- Write tests\n", encoding="utf-8"
    )
    return AdapterContext(
        project_root=tmp_path,
        vibe_dir=vibe_dir,
        constitution="# VIBE.md\nTest constitution",
        standards="# Standards\n\n- Use snake_case\n- Write tests\n",
        architecture="# Architecture\n| Language | Python | - |\n",
        languages=["Python"],
        frameworks=["FastAPI"],
        project_name="test-project",
        enabled_adapters=["agents_md", "claude"],
    )


# ── AGENTS.md Adapter ──


class TestAgentsMd:
    def test_emit_creates_file(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 1
        assert files[0].name == "AGENTS.md"
        assert files[0].exists()

    def test_content_includes_project_info(self, tmp_path: Path) -> None:
        adapter = get_adapter("agents_md")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Python" in content
        assert "FastAPI" in content
        assert "test-project" in content

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


# ── Claude Adapter ──


class TestClaude:
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
        ctx.enabled_adapters = ["claude"]  # No agents_md
        adapter.emit(ctx)
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "@AGENTS.md" not in content
        assert "Python" in content

    def test_rules_have_paths_frontmatter(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        adapter.emit(ctx)
        rules_path = tmp_path / ".claude" / "rules" / "vibe-standards.md"
        content = rules_path.read_text(encoding="utf-8")
        assert "paths:" in content


# ── Cursor Adapter ──


class TestCursor:
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
        content = files_content(tmp_path / ".cursor" / "rules" / "vibe-standards.mdc")
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


# ── Copilot Adapter ──


class TestCopilot:
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


# ── Windsurf Adapter ──


class TestWindsurf:
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


# ── Cline Adapter ──


class TestCline:
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


# ── Roo Code Adapter ──


class TestRoo:
    def test_emit_no_frontmatter(self, tmp_path: Path) -> None:
        adapter = get_adapter("roo")
        assert adapter is not None
        ctx = _make_ctx(tmp_path)
        files = adapter.emit(ctx)
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert not content.startswith("---")
        assert "Vibe Standards" in content


# ── Antigravity Adapter ──


class TestAntigravity:
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
        assert "Python" in content

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


# ── Helpers ──


def files_content(path: Path) -> str:
    return path.read_text(encoding="utf-8")

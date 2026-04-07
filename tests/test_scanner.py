"""Scanner: language, framework, tool detection, and edge cases."""

from __future__ import annotations

from pathlib import Path

from vibe_state.core.scanner import ScanResult, scan_project


class TestScannerDetectsLanguages:
    def test_empty_dir_returns_no_languages(self, tmp_path: Path) -> None:
        result = scan_project(tmp_path)
        assert isinstance(result, ScanResult)
        assert result.languages == []
        assert result.frameworks == []
        assert result.detected_tools == []
        assert result.has_git is False

    def test_detects_python_from_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        result = scan_project(tmp_path)
        assert "Python" in result.languages

    def test_detects_csharp_via_glob(self, tmp_path: Path) -> None:
        (tmp_path / "MyApp.csproj").write_text("<Project/>")
        result = scan_project(tmp_path)
        assert "C#" in result.languages


class TestScannerDetectsFrameworkHints:
    def test_detects_fastapi_dependency(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi"]\n'
        )
        result = scan_project(tmp_path)
        assert "FastAPI" in result.frameworks

    def test_oserror_on_unreadable_file(self, tmp_path: Path) -> None:
        """Scanner handles unreadable files gracefully."""
        # Create a directory named pyproject.toml (will fail read_text)
        (tmp_path / "pyproject.toml").mkdir()
        result = scan_project(tmp_path)
        assert isinstance(result.frameworks, list)


class TestScannerDetectsTools:
    def test_detects_git_directory(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        result = scan_project(tmp_path)
        assert result.has_git is True

    def test_detects_claude_tool(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        result = scan_project(tmp_path)
        assert "claude" in result.detected_tools

    def test_detects_cursor_tool(self, tmp_path: Path) -> None:
        (tmp_path / ".cursor").mkdir()
        result = scan_project(tmp_path)
        assert "cursor" in result.detected_tools

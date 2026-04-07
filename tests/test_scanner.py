"""Tests for project scanner."""

from __future__ import annotations

from pathlib import Path

from vibe_state.core.scanner import ScanResult, scan_project


def test_scan_empty_dir(tmp_path: Path) -> None:
    result = scan_project(tmp_path)
    assert isinstance(result, ScanResult)
    assert result.languages == []
    assert result.frameworks == []
    assert result.detected_tools == []
    assert result.has_git is False


def test_scan_detects_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    result = scan_project(tmp_path)
    assert result.has_git is True


def test_scan_detects_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    result = scan_project(tmp_path)
    assert "Python" in result.languages


def test_scan_detects_claude(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    result = scan_project(tmp_path)
    assert "claude" in result.detected_tools


def test_scan_detects_cursor(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    result = scan_project(tmp_path)
    assert "cursor" in result.detected_tools


def test_scan_detects_framework_hint(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["fastapi"]\n'
    )
    result = scan_project(tmp_path)
    assert "FastAPI" in result.frameworks

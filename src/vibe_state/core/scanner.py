"""Project scanner: detect languages, frameworks, and AI tool signatures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

TOOL_SIGNATURES: dict[str, list[str]] = {
    "claude": [".claude", "CLAUDE.md"],
    "cursor": [".cursor", ".cursorrules"],
    "copilot": [".github/copilot-instructions.md"],
    "windsurf": [".windsurf", ".windsurfrules"],
    "cline": [".clinerules"],
    "roo": [".roo"],
    "antigravity": ["GEMINI.md", ".gemini"],
    "agents_md": ["AGENTS.md"],
}

LANGUAGE_SIGNATURES: dict[str, list[str]] = {
    "Python": ["pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "requirements.txt"],
    "Node.js": ["package.json"],
    "TypeScript": ["tsconfig.json"],
    "Rust": ["Cargo.toml"],
    "Go": ["go.mod"],
    "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "Ruby": ["Gemfile"],
    "PHP": ["composer.json"],
    "C#": ["*.csproj", "*.sln"],
    "Swift": ["Package.swift"],
}

FRAMEWORK_HINTS: dict[str, dict[str, str]] = {
    "pyproject.toml": {
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
    },
    "package.json": {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue",
        "angular": "Angular",
        "svelte": "Svelte",
    },
}


@dataclass
class ScanResult:
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    detected_tools: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    project_root: Path = field(default_factory=lambda: Path.cwd())
    has_git: bool = False


def scan_project(root: Path | None = None) -> ScanResult:
    """Scan project directory and return detection results."""
    project_root = root or Path.cwd()
    result = ScanResult(project_root=project_root)

    # Git detection
    result.has_git = (project_root / ".git").is_dir()

    # AI tool detection
    for tool, signatures in TOOL_SIGNATURES.items():
        for sig in signatures:
            if (project_root / sig).exists():
                if tool not in result.detected_tools:
                    result.detected_tools.append(tool)
                break

    # Language detection via manifest files
    for lang, manifests in LANGUAGE_SIGNATURES.items():
        for manifest in manifests:
            if "*" in manifest:
                if list(project_root.glob(manifest)):
                    result.languages.append(lang)
                    break
            elif (project_root / manifest).exists():
                result.languages.append(lang)
                break

    # Framework hints from manifest content
    for manifest_name, hints in FRAMEWORK_HINTS.items():
        manifest_path = project_root / manifest_name
        if manifest_path.exists():
            try:
                content = manifest_path.read_text(encoding="utf-8").lower()
                for keyword, framework in hints.items():
                    if keyword in content and framework not in result.frameworks:
                        result.frameworks.append(framework)
            except OSError:
                pass

    return result

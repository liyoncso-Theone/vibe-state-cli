"""Jinja2 template rendering engine with i18n support."""

from __future__ import annotations

from datetime import datetime, timezone

from jinja2 import Environment, PackageLoader, TemplateNotFound, select_autoescape

from vibe_state import __version__

SUPPORTED_LANGS = {"en", "zh-TW"}

# Module-level cached environment
_env: Environment | None = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(
            loader=PackageLoader("vibe_state", "templates"),
            autoescape=select_autoescape([]),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _env


def _resolve_template(template_path: str, lang: str) -> str:
    """Resolve template path with i18n fallback."""
    if lang != "en":
        localized = f"{lang}/{template_path}"
        try:
            _get_env().get_template(localized)
            return localized
        except TemplateNotFound:
            pass
    return template_path


def render_template(template_path: str, lang: str = "en", **context: object) -> str:
    """Render a Jinja2 template with the given context."""
    env = _get_env()
    context.setdefault("version", __version__)
    context.setdefault("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    context.setdefault("languages", [])
    context.setdefault("frameworks", [])
    context.setdefault("project_name", "")
    context.setdefault("stale_task_days", 30)

    resolved = _resolve_template(template_path, lang)
    template = env.get_template(resolved)
    return template.render(**context)


def render_all_state_files(
    languages: list[str],
    frameworks: list[str],
    project_name: str = "",
    stale_task_days: int = 30,
    lang: str = "en",
) -> dict[str, str]:
    """Render all .vibe/ files. Returns {relative_path: content}."""
    ctx = {
        "languages": languages,
        "frameworks": frameworks,
        "project_name": project_name,
        "stale_task_days": stale_task_days,
    }

    files: dict[str, str] = {}

    # VIBE.md (constitution)
    files["VIBE.md"] = render_template("vibe.md.j2", lang=lang, **ctx)

    # state/ files
    for name in ["architecture", "current", "tasks", "standards", "archive", "experiments"]:
        files[f"state/{name}.md"] = render_template(
            f"state/{name}.md.j2", lang=lang, **ctx
        )

    return files

"""Adapter registry: auto-discover and manage all built-in adapters."""

from __future__ import annotations

from pathlib import Path

from vibe_state.adapters.base import AdapterBase

# Registry populated at module load time
_ADAPTERS: dict[str, type[AdapterBase]] = {}


def register_adapter(adapter_cls: type[AdapterBase]) -> type[AdapterBase]:
    """Register an adapter class. Used as decorator."""
    _ADAPTERS[adapter_cls.name] = adapter_cls
    return adapter_cls


def get_adapter(name: str) -> AdapterBase | None:
    """Get an adapter instance by name."""
    cls = _ADAPTERS.get(name)
    return cls() if cls else None


def get_all_adapter_names() -> list[str]:
    """Get all registered adapter names."""
    return list(_ADAPTERS.keys())


def get_all_adapters() -> dict[str, AdapterBase]:
    """Get instances of all registered adapters."""
    return {name: cls() for name, cls in _ADAPTERS.items()}


def detect_tools(project_root: Path) -> list[str]:
    """Detect which AI tools are present in the project."""
    detected = []
    for name, cls in _ADAPTERS.items():
        adapter = cls()
        if adapter.detect(project_root):
            detected.append(name)
    return detected


def _load_all_adapters() -> None:
    """Import all adapter modules to trigger registration."""
    from vibe_state.adapters import (  # noqa: F401
        agents_md,
        antigravity,
        claude,
        cline,
        copilot,
        cursor,
        roo,
        windsurf,
    )


# Auto-load on first import
_load_all_adapters()

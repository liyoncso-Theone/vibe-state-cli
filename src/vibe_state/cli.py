"""CLI entry point for vibe-state-cli.

Thin assembler: imports command modules to trigger @app.command() registration,
then re-exports ``app`` for the console-script entry point.
"""

from __future__ import annotations

# Import app and console from helpers (single source of truth)
from vibe_state.commands._helpers import (  # noqa: F401
    app,
    console,
)
from vibe_state.commands._helpers import (
    check_fingerprint as _check_fingerprint,
)
from vibe_state.commands._helpers import (
    extract_latest_progress as _extract_latest_progress,
)
from vibe_state.commands._helpers import (
    extract_section_items as _extract_section_items,
)
from vibe_state.commands._helpers import (
    read_known_fingerprints as _read_known_fingerprints,
)

# Backward-compatible re-exports used by tests
__all__ = [
    "app",
    "console",
    "_check_fingerprint",
    "_extract_latest_progress",
    "_extract_section_items",
    "_read_known_fingerprints",
    "adapt",
    "init",
    "start",
    "status",
    "sync",
]

# Import command modules to register @app.command() handlers
from vibe_state.commands.cmd_adapt import adapt  # noqa: F401
from vibe_state.commands.cmd_init import init  # noqa: F401
from vibe_state.commands.cmd_start import start  # noqa: F401
from vibe_state.commands.cmd_status import status  # noqa: F401
from vibe_state.commands.cmd_sync import sync  # noqa: F401

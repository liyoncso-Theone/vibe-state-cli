"""CLI entry point for vibe-state-cli.

Thin assembler: imports command modules to trigger @app.command() registration,
then re-exports ``app`` for the console-script entry point.
"""

from __future__ import annotations

from vibe_state.commands._helpers import app, console  # noqa: F401

# Import command modules to register @app.command() handlers
from vibe_state.commands.cmd_adapt import adapt  # noqa: F401
from vibe_state.commands.cmd_init import init  # noqa: F401
from vibe_state.commands.cmd_start import start  # noqa: F401
from vibe_state.commands.cmd_status import status  # noqa: F401
from vibe_state.commands.cmd_sync import sync  # noqa: F401

"""CLI entry point for vibe-state-cli.

Thin assembler: imports command modules to trigger @app.command() registration,
then re-exports ``app`` for the console-script entry point.
"""

from __future__ import annotations

import contextlib
import sys


def _force_utf8_io() -> None:
    """Force UTF-8 on stdout/stderr.

    Windows legacy code pages (cp950, cp936, cp932) cannot encode the box
    drawing characters and ✓ ⚠ ✗ markers that Rich emits, so `vibe status`
    crashes on Windows CMD / PowerShell 5 / CJK Windows defaults with
    `UnicodeEncodeError: 'cp950' codec can't encode character '\\u2713'`.
    Reconfiguring at startup means users don't have to set
    `PYTHONIOENCODING=utf-8` themselves.

    No-op on POSIX (already UTF-8). Safe in test runners — IO stubs that
    don't support `reconfigure` are silently skipped.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding == "utf8":
            continue
        with contextlib.suppress(AttributeError, OSError):
            stream.reconfigure(encoding="utf-8", errors="replace")


_force_utf8_io()


from vibe_state.commands._helpers import app, console  # noqa: E402, F401

# Import command modules to register @app.command() handlers
from vibe_state.commands.cmd_adapt import adapt  # noqa: E402, F401
from vibe_state.commands.cmd_init import init  # noqa: E402, F401
from vibe_state.commands.cmd_start import start  # noqa: E402, F401
from vibe_state.commands.cmd_status import status  # noqa: E402, F401
from vibe_state.commands.cmd_sync import sync  # noqa: E402, F401

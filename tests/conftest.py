"""Shared pytest fixtures.

By default, suppress git post-commit hook installation across all tests so
that real `git commit` invocations inside tests don't fire `vibe sync` and
mutate the cursor under us. Tests that exercise hook installation explicitly
delete the environment variable in their own scope.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_hook_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBE_SKIP_HOOK_INSTALL", "1")

# Contributing to vibe-state-cli

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/vibe-state-cli/vibe-state-cli.git
cd vibe-state-cli
make install              # Uses uv sync + pre-commit install
```

Requires [uv](https://docs.astral.sh/uv/) (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`).

## Running Tests

```bash
make lint                 # uv run ruff check
make test                 # uv run pytest
make cov                  # uv run pytest --cov
make typecheck            # uv run mypy
make build                # uv build
```

## Dependency Management

Dependencies are locked via `uv.lock` (committed to git). This guarantees every contributor gets the exact same versions.

```bash
# After adding a dependency to pyproject.toml:
make lock                 # Regenerates uv.lock
```

## Project Structure

```text
src/vibe_state/
├── cli.py              # Thin entry point (imports commands/)
├── config.py           # config.toml schema (Pydantic)
├── safety.py           # Backups for adapter operations
├── commands/           # 5 CLI commands (modular)
│   ├── _helpers.py     # Shared utils, app definition, --verbose
│   ├── cmd_init.py     # vibe init (scan + migrate + generate)
│   ├── cmd_start.py    # vibe start
│   ├── cmd_sync.py     # vibe sync
│   ├── cmd_status.py   # vibe status
│   └── cmd_adapt.py    # vibe adapt
├── core/               # Core logic (no CLI dependency)
│   ├── scanner.py      # Language/framework/tool detection
│   ├── lifecycle.py    # State machine (UNINIT/READY/ACTIVE/CLOSED)
│   ├── git_ops.py      # Git read-only + autoresearch detection
│   ├── state.py        # Atomic file I/O
│   ├── compactor.py    # AST-based Markdown compression
│   ├── migrator.py     # Legacy file detection + rule import
│   └── templates.py    # Jinja2 rendering with i18n
├── adapters/           # 8 built-in adapters
│   ├── base.py         # AdapterBase ABC + shared logic
│   ├── registry.py     # Auto-discovery via @register_adapter
│   └── *.py            # One file per adapter
└── templates/          # Jinja2 templates (en + zh-TW)
```

## Adding a New Adapter

1. Create `src/vibe_state/adapters/your_tool.py`
2. Inherit from `AdapterBase`, implement `detect()`, `emit()`, `clean()`
3. Add `@register_adapter` decorator
4. Add import to `registry.py:_load_all_adapters()`
5. Add detection signature to `scanner.py:TOOL_SIGNATURES`
6. Add tests to `tests/test_adapters.py`
7. Update `README.md` supported tools table

Note: `_build_common_body()` in `base.py` includes a "Vibe Commands" section in all adapter output that instructs AI tools to execute vibe CLI commands in the terminal. If the target tool supports [Agent Skills](https://agentskills.io/) (`.claude/skills/*/SKILL.md`), consider generating skill files in `emit()` — see `claude.py` for reference.

## Commit Convention

- Follow [Conventional Commits](https://www.conventionalcommits.org/)
- One logical change per commit
- Prefix: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## Code Standards

- Python 3.10+, type annotations everywhere
- `pathlib.Path` for all file operations (no string concatenation)
- `encoding="utf-8"` + `newline="\n"` on all file I/O
- No `shell=True` in subprocess calls
- Ruff for linting, mypy for type checking

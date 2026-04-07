# Contributing to vibe-state-cli

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/vibe-state-cli/vibe-state-cli.git
cd vibe-state-cli
pip install -e ".[dev]"
```

## Running Tests

```bash
ruff check src/ tests/    # Lint
pytest tests/ -v          # Tests
```

## Project Structure

```
src/vibe_state/
├── cli.py            # 5 Typer commands
├── config.py         # config.toml schema (Pydantic)
├── safety.py         # Snapshots, backups, dry-run
├── core/
│   ├── scanner.py    # Language/framework/tool detection
│   ├── lifecycle.py  # State machine (UNINIT→READY→ACTIVE→CLOSED)
│   ├── git_ops.py    # Git read-only + autoresearch detection
│   ├── state.py      # Atomic file I/O with locking
│   ├── compactor.py  # Task archival + state compression
│   └── templates.py  # Jinja2 rendering with i18n
├── adapters/         # 8 built-in adapters
│   ├── base.py       # AdapterBase ABC + _build_common_body()
│   ├── registry.py   # Auto-discovery via @register_adapter
│   └── *.py          # One file per adapter
└── templates/        # Jinja2 templates (en + zh-TW)
```

## Adding a New Adapter

1. Create `src/vibe_state/adapters/your_tool.py`
2. Inherit from `AdapterBase`, implement `detect()`, `emit()`, `clean()`
3. Add `@register_adapter` decorator
4. Add import to `registry.py:_load_all_adapters()`
5. Add detection signature to `scanner.py:TOOL_SIGNATURES`
6. Add tests to `tests/test_adapters.py`
7. Update `README.md` supported tools table

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

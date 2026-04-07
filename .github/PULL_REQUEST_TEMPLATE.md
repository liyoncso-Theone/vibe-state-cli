## What does this PR do?

<!-- One sentence summary -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] New adapter
- [ ] Refactor (no behavior change)
- [ ] Documentation
- [ ] CI/CD

## Checklist

- [ ] `ruff check src/ tests/` passes
- [ ] `pytest tests/ --cov=vibe_state` shows no regression
- [ ] New code has tests (coverage must not decrease)
- [ ] Updated CHANGELOG.md if user-facing change
- [ ] Updated docs if behavior changed

## Adapter PR (if applicable)

- [ ] Inherits `AdapterBase` with `detect()`, `emit()`, `clean()`, `validate()`
- [ ] `@register_adapter` decorator applied
- [ ] Added to `registry.py:_load_all_adapters()`
- [ ] Added to `scanner.py:TOOL_SIGNATURES`
- [ ] Tests in `test_adapters.py`
- [ ] Updated README supported tools table

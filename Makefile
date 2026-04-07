.PHONY: install lint test cov clean build lock sync

## Install all dependencies (runtime + dev) from lockfile — reproducible
install:
	uv sync --all-extras
	uv run pre-commit install

## Regenerate uv.lock from pyproject.toml
lock:
	uv lock

## Run linter
lint:
	uv run ruff check src/ tests/

## Run tests
test:
	uv run pytest tests/ -v --tb=short

## Run tests with coverage
cov:
	uv run pytest tests/ --cov=vibe_state --cov-report=term-missing

## Type check
typecheck:
	uv run mypy src/vibe_state/ --ignore-missing-imports

## Clean build artifacts
clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +

## Build distribution
build:
	uv build

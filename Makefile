.PHONY: install lint test cov clean build

## Install dev dependencies
install:
	pip install -e ".[dev]"
	pre-commit install

## Run linter
lint:
	ruff check src/ tests/

## Run tests
test:
	pytest tests/ -v --tb=short

## Run tests with coverage
cov:
	pytest tests/ --cov=vibe_state --cov-report=term-missing

## Clean build artifacts
clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +

## Build distribution
build:
	python -m build

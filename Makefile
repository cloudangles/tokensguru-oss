.PHONY: help install lint format typecheck test coverage audit build check clean

PY ?= python

help:  ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install:  ## Install the package and dev tools in editable mode
	$(PY) -m pip install -e ".[dev]"

lint:  ## Check code style and common bugs
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:  ## Auto-format the code
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

typecheck:  ## Strict type checking of the package
	$(PY) -m mypy

test:  ## Run the test suite
	$(PY) -m pytest

coverage:  ## Run tests with the coverage gate (fails under 80%)
	$(PY) -m pytest --cov --cov-report=term-missing

audit:  ## Check installed dependencies for known vulnerabilities
	$(PY) -m pip_audit --progress-spinner off

build:  ## Build the wheel and sdist, then check the metadata
	rm -rf dist build
	$(PY) -m build
	$(PY) -m twine check dist/*

check: lint typecheck coverage build  ## Run everything CI runs (except audit)

clean:  ## Remove build and cache output
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage
	find src -name __pycache__ -type d -prune -exec rm -rf {} +

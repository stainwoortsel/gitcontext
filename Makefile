.PHONY: help install dev-install test test-cov lint format clean build publish docs

help:
	@echo "Available commands:"
	@echo "  install      - Install package"
	@echo "  dev-install  - Install in development mode"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  lint         - Run linters"
	@echo "  format       - Format code"
	@echo "  clean        - Clean build artifacts"
	@echo "  build        - Build package"
	@echo "  publish      - Publish to PyPI"
	@echo "  docs         - Build documentation"

install:
	pip install .

dev-install:
	pip install -e ".[dev,test,docs]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=gitcontext --cov-report=term --cov-report=html

lint:
	flake8 src/gitcontext
	mypy src/gitcontext

format:
	black src/gitcontext tests
	isort src/gitcontext tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

build: clean
	python -m build

publish: build
	twine check dist/*
	twine upload dist/*

docs:
	mkdocs build

serve-docs:
	mkdocs serve

.PHONY: pre-commit
pre-commit: format lint test

.PHONY: install dev-install test lint format clean build

install:
	pip install .

dev-install:
	pip install -e .[dev]

test:
	pytest tests/ --cov=sysagent --cov-report=term-missing

lint:
	ruff check sysagent tests
	mypy sysagent

format:
	black sysagent tests
	ruff check --fix sysagent tests

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov .mypy_cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

build:
	python -m build

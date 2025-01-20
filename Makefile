#* Variables
SHELL := /usr/bin/env bash -o pipefail -o errexit

#* Lockfile handling
lockfile-update:
	poetry lock -n

lockfile-update-full:
	poetry lock -n --regenerate

#* Installation
install:
	poetry install -n

install-types:
	poetry run mypy --install-types --non-interactive ./

#* Poetry
poetry-download:
	curl -sSL https://install.python-poetry.org | python -

#* Formatters
codestyle:
	poetry run pyupgrade --exit-zero-even-if-changed --py39-plus **/*.py
	poetry run isort --settings-path pyproject.toml ./
	poetry run black --config pyproject.toml ./

formatting: codestyle

#* Linting
test:
	poetry run pytest -c pyproject.toml tests/

check-codestyle:
	poetry run isort --diff --check-only --settings-path pyproject.toml ./
	poetry run black --diff --check --config pyproject.toml ./
	poetry run darglint --verbosity 2 hyperliquid tests

check:
	poetry run mypy --config-file pyproject.toml ./

check-safety:
	poetry check
	poetry run safety check --full-report
	poetry run bandit -ll --recursive hyperliquid tests

lint: test check-codestyle mypy check-safety

update-dev-deps:
	poetry add -D bandit@latest darglint@latest "isort[colors]@latest" mypy@latest pre-commit@latest pydocstyle@latest pylint@latest pytest@latest pyupgrade@latest safety@latest coverage@latest coverage-badge@latest pytest-cov@latest
	poetry add -D --allow-prereleases black@latest

#* Cleaning
pycache-remove:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

dsstore-remove:
	find . | grep -E ".DS_Store" | xargs rm -rf

mypycache-remove:
	find . | grep -E ".mypy_cache" | xargs rm -rf

ipynbcheckpoints-remove:
	find . | grep -E ".ipynb_checkpoints" | xargs rm -rf

pytestcache-remove:
	find . | grep -E ".pytest_cache" | xargs rm -rf

build-remove:
	rm -rf build/

cleanup: pycache-remove dsstore-remove mypycache-remove ipynbcheckpoints-remove pytestcache-remove

.PHONY: all $(MAKECMDGOALS)

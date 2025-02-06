# Define the shell to use when executing commands
SHELL := /usr/bin/env bash -o pipefail -o errexit

help:
	@@grep -h '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-22s%s\n", $$1, $$2}' | sort

lockfile-update:	## Update poetry.lock
	poetry lock -n

lockfile-update-full:	## Fully regenerate poetry.lock
	poetry lock -n --regenerate

install:	## Install dependencies from poetry.lock
	poetry install -n

install-types:	## Find and install additional types for mypy
	poetry run mypy --install-types --non-interactive ./

poetry-download:	## Download and install poetry
	curl -sSL https://install.python-poetry.org | python -

lint: pre-commit	## Alias for the pre-commit target

pre-commit:  ## Run linters + formatters via pre-commit, run "make pre-commit hook=black" to run only black
	poetry run pre-commit run --all-files --verbose --show-diff-on-failure --color always $(hook)

test:	## Run tests with pytest
	poetry run pytest -c pyproject.toml tests/

check-safety:	## Run safety checks on dependencies
	poetry run safety check --full-report

update-dev-deps:	## Update development dependencies to latest versions
	poetry add -D mypy@latest pre-commit@latest pytest@latest safety@latest coverage@latest pytest-cov@latest
	poetry run pre-commit autoupdate

cleanup: ## Cleanup project
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf
	find . | grep -E ".DS_Store" | xargs rm -rf
	find . | grep -E ".mypy_cache" | xargs rm -rf
	find . | grep -E ".pytest_cache" | xargs rm -rf
	rm -rf build/

.PHONY: all $(MAKECMDGOALS)

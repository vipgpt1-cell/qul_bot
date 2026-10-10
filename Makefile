.PHONY: install check lint format typecheck test test-pg run migrate migration

PY := .venv/bin/python

install:
	uv venv --python 3.13 .venv || python3 -m venv .venv
	uv pip install --python $(PY) -e ".[dev]" || $(PY) -m pip install -e ".[dev]"

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff check . --fix
	$(PY) -m ruff format .

typecheck:
	$(PY) -m mypy

test:
	$(PY) -m pytest

# Needs a reachable PostgreSQL, e.g.:
#   make test-pg TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/qul_test
test-pg:
	TEST_DATABASE_URL=$(TEST_DATABASE_URL) $(PY) -m pytest

check: lint typecheck test

run: migrate
	$(PY) -m qul_bot

migrate:
	.venv/bin/alembic upgrade head

# make migration m="add something"   (generate against Postgres: add -x batch=0)
migration:
	.venv/bin/alembic revision --autogenerate -m "$(m)"

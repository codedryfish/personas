.PHONY: install run test fmt lint

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

run:
	$(UVICORN) persona_sim.app.main:app --reload --env-file .env

test:
	$(PYTEST)

fmt:
	$(RUFF) format src tests

lint:
	$(RUFF) check src tests

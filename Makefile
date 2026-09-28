.DEFAULT_GOAL := help
BACKEND_PORT ?= 8000
# 0.0.0.0 lets phones on your network reach the API (see mobile/README.md).
BACKEND_HOST ?= 127.0.0.1
FRONTEND_PORT ?= 5173
.PHONY: help setup dev backend frontend mobile migrate seed check check-backend check-frontend check-mobile smoke

help:
	@printf '%s\n' 'make setup          Install locked dependencies; create .env if absent' 'make dev            Start backend and frontend; Ctrl+C stops both' 'make backend        Start only the backend with reload' 'make frontend       Start only the frontend' 'make mobile         Start the Expo app (press w for web)' 'make migrate        Apply migrations to the configured database' 'make seed           Load or update the crop catalogue (safe to repeat)' 'make check          Run backend and frontend checks (Chromium required)' 'make check-backend  Run Ruff and pytest' 'make check-frontend Run lint, formatting, build, and mocked browser tests' 'make check-mobile   Run mobile lint, types, unit, API-type and browser tests' 'make smoke          Build and test the full stack in disposable Docker containers'

setup:
	uv sync --all-packages --locked
	uv run --no-sync python -m scripts.setup_env
	npm --prefix frontend ci
	npm --prefix mobile ci

dev:
	uv run --no-sync python -m scripts.dev --backend-port $(BACKEND_PORT) --frontend-port $(FRONTEND_PORT)

backend:
	uv run --no-sync uvicorn backend.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

frontend:
	npm --prefix frontend run dev

mobile:
	npm --prefix mobile run start

migrate:
	uv run --no-sync alembic -c backend/alembic.ini upgrade head

seed:
	uv run --no-sync python -m backend.seed

check: check-backend check-frontend check-mobile

check-backend:
	uv run --no-sync ruff check .
	uv run --no-sync ruff format --check .
	uv run --no-sync pytest

check-frontend:
	npm --prefix frontend run lint
	npm --prefix frontend run format:check
	npm --prefix frontend run build
	npm --prefix frontend test

check-mobile:
	npm --prefix mobile run lint
	npm --prefix mobile run format:check
	npm --prefix mobile run typecheck
	npm --prefix mobile run test:unit
	npm --prefix mobile run api:check
	npm --prefix mobile run test:e2e

smoke:
	bash scripts/smoke.sh

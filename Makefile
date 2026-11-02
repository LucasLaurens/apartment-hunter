.DEFAULT_GOAL := full
.PHONY: lint check format analyze test full install-hooks dev run ui-check audit

HOST ?= 127.0.0.1
PORT ?= 8001

dev: ## Local web interface with hot-reload (HOST/PORT overridable)
	uv run hunt serve --host $(HOST) --port $(PORT) --reload

run: ## One-shot crawl + display (pass ARGS="--city Lyon")
	uv run hunt search $(ARGS)

ui-check: ## Audit thème/accessibilité de l'UI web (serveur déjà lancé via `make dev`)
	uv run python scripts/verify_ui.py http://$(HOST):$(PORT)/

lint: ## Ruff linter
	uv run ruff check src tests

check: ## Verify formatting (no writes)
	uv run ruff format --check src tests

format: ## Apply formatting
	uv run ruff format src tests

analyze: ## Static type analysis
	uv run mypy src

test: ## Run test suite with coverage
	uv run pytest

full: lint check analyze test ## Run everything (CI)

audit: ## Known vulnerabilities in the locked dependencies (pip-audit, fetched for the run only)
	uv export --quiet --frozen --extra dev --no-hashes --no-emit-project | uvx pip-audit --requirement /dev/stdin --progress-spinner off

install-hooks: ## Install git hooks (pre-commit, pre-push gate, commit identity)
	uv run pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg


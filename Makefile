# cryptoscope developer commands.
# Run `make help` to see the available targets.
#
# Every command uses Docker and Docker Compose so the only dependency on the
# host is Docker. The test and lint commands route through
# docker-compose.tests.yml which mounts the source tree as a bind volume.

SHELL := /bin/bash
COMPOSE := docker compose
COMPOSE_TEST := docker compose -f docker-compose.tests.yml
# Service short names used to build docker-compose.tests.yml service names.
GO_SERVICE_NAMES := ingest processor gateway
PY_SERVICE_NAMES := command query alert
GO_SERVICES := ingest-service stream-processor api-gateway
PY_SERVICES := command-service query-service alert-service

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'


# ── Full stack lifecycle ───────────────────────────────────────────────

.PHONY: up
up: ## Start all services (backend + frontend via Docker)
	$(COMPOSE) up -d --build

.PHONY: up-all
up-all: ## Start backend services + frontend dev server with hot-reload
	$(COMPOSE) up -d --build postgres clickhouse mongo redis zookeeper kafka \
		otel-collector prometheus grafana \
		ingest-service stream-processor command-service query-service api-gateway alert-service
	@echo ""
	@echo "==> Backend services started. Starting frontend dev server..."
	@echo "    Frontend will be at http://localhost:5173"
	@echo "    (hot-reload enabled; proxies /api -> api-gateway:8080)"
	@echo ""
	cd frontend && npm run dev

.PHONY: down
down: ## Stop the stack and remove volumes
	$(COMPOSE) down -v

.PHONY: restart
restart: ## Restart a service (usage: make restart svc=api-gateway)
	$(COMPOSE) restart $(svc)

.PHONY: ps
ps: ## List running services
	$(COMPOSE) ps

.PHONY: logs
logs: ## Tail logs from all services
	$(COMPOSE) logs -f

.PHONY: build
build: ## Build all Docker images without starting
	$(COMPOSE) build

.PHONY: clean
clean: ## Remove all containers, volumes, and build cache
	$(COMPOSE) down -v --rmi all --remove-orphans
	docker builder prune -f


# ── Shell access ───────────────────────────────────────────────────────

.PHONY: shell
shell: ## Open a shell in a running service (usage: make shell svc=api-gateway)
	$(COMPOSE) exec $(svc) /bin/sh

.PHONY: shell-go
shell-go: ## Open a Go dev shell (useful for interactive go work)
	docker run --rm -it \
		-v $(PWD):/app -w /app \
		golang:1.25-alpine /bin/sh

.PHONY: shell-python
shell-python: ## Open a Python dev shell
	docker run --rm -it \
		-v $(PWD):/app -w /app/services/command-service \
		python:3.12-slim /bin/bash


# ── Database ───────────────────────────────────────────────────────────

.PHONY: migrate
migrate: ## Run alembic migrations for the command service
	$(COMPOSE) exec command-service alembic upgrade head

.PHONY: migrate-new
migrate-new: ## Create a new migration (usage: make migrate-new msg="add table")
	$(COMPOSE) exec command-service alembic revision --autogenerate -m "$(msg)"

.PHONY: seed
seed: ## Seed a demo tenant and tracked symbols
	./scripts/bootstrap.sh


# ── Protobuf ───────────────────────────────────────────────────────────

.PHONY: proto
proto: ## Regenerate protobuf stubs for Go and Python
	$(COMPOSE_TEST) run --rm proto


# ── Frontend ─────────────────────────────────────────────────────────

.PHONY: frontend
frontend: ## Build the React frontend for production
	cd frontend && npm ci && npm run build

.PHONY: frontend-dev
frontend-dev: ## Start Vite dev server on the host (requires backend running)
	cd frontend && npm run dev


# ── Tests ──────────────────────────────────────────────────────────────

.PHONY: test
test: test-go test-python ## Run all test suites

.PHONY: test-all
test-all: test ## Alias for `make test`

.PHONY: test-go
test-go: ## Run all Go unit tests
	@for svc in $(GO_SERVICE_NAMES); do \
		echo "==> testing test-$$svc"; \
		$(COMPOSE_TEST) run --rm test-$$svc || exit 1; \
	done
	@echo "==> testing libs/go"
	$(COMPOSE_TEST) run --rm test-libs-go

.PHONY: test-python
test-python: ## Run all Python unit tests
	@for svc in $(PY_SERVICE_NAMES); do \
		echo "==> testing test-$$svc"; \
		$(COMPOSE_TEST) run --rm test-$$svc || exit 1; \
	done
	@echo "==> testing libs/python"
	$(COMPOSE_TEST) run --rm test-libs-python


# ── Linting ────────────────────────────────────────────────────────────

.PHONY: lint
lint: lint-go lint-python lint-frontend ## Run all linters

.PHONY: lint-go
lint-go: ## Lint all Go code
	$(COMPOSE_TEST) run --rm lint-go

.PHONY: lint-python
lint-python: ## Lint and type check all Python code
	$(COMPOSE_TEST) run --rm lint-python

.PHONY: lint-frontend
lint-frontend: ## Type check the frontend code
	$(COMPOSE_TEST) run --rm lint-frontend


# ─── One-off test targets (run a single service's tests) ───────────────

.PHONY: test-ingest
test-ingest: ## Run ingest-service tests
	$(COMPOSE_TEST) run --rm test-ingest

.PHONY: test-processor
test-processor: ## Run stream-processor tests
	$(COMPOSE_TEST) run --rm test-processor

.PHONY: test-gateway
test-gateway: ## Run api-gateway tests
	$(COMPOSE_TEST) run --rm test-gateway

.PHONY: test-command
test-command: ## Run command-service tests
	$(COMPOSE_TEST) run --rm test-command

.PHONY: test-query
test-query: ## Run query-service tests
	$(COMPOSE_TEST) run --rm test-query

.PHONY: test-alert
test-alert: ## Run alert-service tests
	$(COMPOSE_TEST) run --rm test-alert

.PHONY: test-libs-go
test-libs-go: ## Run Go shared library tests
	$(COMPOSE_TEST) run --rm test-libs-go

.PHONY: test-libs-python
test-libs-python: ## Run Python shared library tests
	$(COMPOSE_TEST) run --rm test-libs-python

# cryptoscope developer commands.
# Run `make help` to see the available targets.

SHELL := /bin/bash
COMPOSE := docker compose
GO_SERVICES := ingest-service stream-processor api-gateway
PY_SERVICES := query-service command-service alert-service

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: up
up: ## Start the full stack with Docker Compose
	$(COMPOSE) up -d --build

.PHONY: down
down: ## Stop the stack and remove volumes
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail logs from all services
	$(COMPOSE) logs -f

.PHONY: bootstrap
bootstrap: ## Seed a demo tenant and tracked symbols
	./scripts/bootstrap.sh

.PHONY: proto
proto: ## Regenerate protobuf stubs for Go and Python
	./scripts/gen_proto.sh

.PHONY: test
test: test-go test-python ## Run all test suites

.PHONY: test-go
test-go: ## Run Go unit and integration tests
	@for svc in $(GO_SERVICES); do \
		echo "==> testing $$svc"; \
		( cd services/$$svc && go test ./... ) || exit 1; \
	done
	@echo "==> testing libs/go"; ( cd libs/go && go test ./... )

.PHONY: test-python
test-python: ## Run Python unit and integration tests
	@for svc in $(PY_SERVICES); do \
		echo "==> testing $$svc"; \
		( cd services/$$svc && python -m pytest ) || exit 1; \
	done

.PHONY: lint
lint: lint-go lint-python ## Run all linters

.PHONY: lint-go
lint-go: ## Lint Go services
	@for svc in $(GO_SERVICES); do \
		echo "==> linting $$svc"; \
		( cd services/$$svc && gofmt -l . && go vet ./... ) || exit 1; \
	done

.PHONY: lint-python
lint-python: ## Lint and type check Python services
	@for svc in $(PY_SERVICES); do \
		echo "==> linting $$svc"; \
		( cd services/$$svc && ruff check . && mypy src ) || exit 1; \
	done

.PHONY: e2e
e2e: ## Run the end-to-end suite against the compose stack
	./scripts/e2e.sh

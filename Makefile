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
up: ## Apply database migrations, then start all services via Docker
	$(COMPOSE) --profile dev run --build --rm --no-deps command-service alembic upgrade head
	$(COMPOSE) --profile dev up -d --build
	./scripts/bootstrap.sh

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
	$(COMPOSE) --profile dev down -v

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
test: test-go test-python test-frontend ## Run all test suites

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

.PHONY: test-frontend
test-frontend: ## Run frontend unit tests
	$(COMPOSE_TEST) run --rm test-frontend


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


# ── Kubernetes deployment ─────────────────────────────────────────────

K8S_OVERLAY ?= overlays/production
K8S_BASE := deploy/k8s

.PHONY: k8s-build
k8s-build: ## Build and tag Docker images for Kubernetes
	@echo "==> building Docker images"
	for svc in $(GO_SERVICES) $(PY_SERVICES); do \
		echo "--- $$svc ---"; \
		docker build -t cryptoscope/$$svc:latest -f services/$$svc/Dockerfile .; \
	done
	@echo "==> building frontend"
	docker build -t cryptoscope/frontend:latest -f frontend/Dockerfile frontend/

.PHONY: k8s-deploy
k8s-deploy: ## Deploy to Kubernetes (usage: make k8s-deploy K8S_OVERLAY=overlays/production)
	@echo "==> deploying with kustomize ($(K8S_OVERLAY))"
	kubectl apply -k $(K8S_BASE)/$(K8S_OVERLAY)

.PHONY: k8s-delete
k8s-delete: ## Delete Kubernetes resources (usage: make k8s-delete K8S_OVERLAY=overlays/production)
	@echo "==> deleting with kustomize ($(K8S_OVERLAY))"
	kubectl delete -k $(K8S_BASE)/$(K8S_OVERLAY) --ignore-not-found

.PHONY: k8s-diff
k8s-diff: ## Show what kustomize would apply (dry-run)
	@echo "==> dry-run apply ($(K8S_OVERLAY))"
	kubectl apply -k $(K8S_BASE)/$(K8S_OVERLAY) --dry-run=client

.PHONY: k8s-status
k8s-status: ## Show status of cryptoscope pods and services
	kubectl -n cryptoscope get pods,svc,ingress -l app.kubernetes.io/part-of=cryptoscope

.PHONY: k8s-logs
k8s-logs: ## Tail logs from all cryptoscope pods
	kubectl -n cryptoscope logs -l app.kubernetes.io/part-of=cryptoscope --tail=100 -f

.PHONY: k8s-portforward
k8s-portforward: ## Forward api-gateway to localhost:8080
	kubectl -n cryptoscope port-forward svc/api-gateway 8080:8080 &
	@echo "==> api-gateway available at http://localhost:8080"

.PHONY: k8s-deploy-staging
k8s-deploy-staging: ## Deploy to staging cluster via kustomize
	@echo "==> deploying to staging"
	kubectl apply -k $(K8S_BASE)/overlays/staging
	kubectl -n cryptoscope-staging rollout status deployment/api-gateway --timeout=120s
	kubectl -n cryptoscope-staging rollout status deployment/query-service --timeout=120s
	kubectl -n cryptoscope-staging rollout status deployment/command-service --timeout=120s
	@echo "==> staging deploy complete"

.PHONY: k8s-status-staging
k8s-status-staging: ## Show staging cluster status
	kubectl -n cryptoscope-staging get pods,svc,ingress

.PHONY: k8s-logs-staging
k8s-logs-staging: ## Tail logs from staging pods
	kubectl -n cryptoscope-staging logs -l app.kubernetes.io/part-of=cryptoscope --tail=100 -f

# ── Docker Swarm deployment ──────────────────────────────────────────

SWARM_STACK := cryptoscope
SWARM_SECRETS := postgres_dsn redis_password mongo_uri clickhouse_user clickhouse_password kafka_sasl_username kafka_sasl_password kafka_ca

.PHONY: swarm-secrets
swarm-secrets: ## Create Docker secrets from ./secrets/ files (idempotent)
	@echo "==> creating Swarm secrets from ./secrets/"
	@for name in $(SWARM_SECRETS); do \
		file="secrets/$$name.txt"; \
		if [ ! -f "$$file" ]; then \
			echo "    missing $${file} (create it first)"; \
		elif docker secret inspect "$$name" >/dev/null 2>&1; then \
			echo "    $$name already exists, skipping"; \
		else \
			docker secret create "$$name" "$$file" >/dev/null && echo "    created $$name"; \
		fi; \
	done

.PHONY: swarm-deploy
swarm-deploy: ## Deploy the production stack to a Swarm manager (docker stack deploy)
	@echo "==> deploying stack $(SWARM_STACK)"
	docker stack deploy -c docker-compose.prod.yml $(SWARM_STACK)
	@echo "==> check status with: docker stack services $(SWARM_STACK)"

.PHONY: swarm-remove
swarm-remove: ## Remove the production stack from Swarm
	@echo "==> removing stack $(SWARM_STACK)"
	docker stack rm $(SWARM_STACK)

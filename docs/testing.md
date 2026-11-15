# Testing and static checks

The project defines test and lint runners in `docker-compose.tests.yml`; Make targets are the supported shortcuts. Docker Compose v2 is required. Services use bind-mounted source for most test commands. Python test images install their service dependencies at build/start time as configured in Compose.

## Run suites

```sh
make test                 # Go, Python, and frontend suites
make test-go              # all Go service modules and Go shared libraries
make test-python          # all Python services and shared Python package
make test-frontend        # Vitest suite
```

Focused targets include `make test-ingest`, `make test-processor`, `make test-gateway`, `make test-command`, `make test-query`, `make test-alert`, `make test-libs-go`, and `make test-libs-python`.

## Lint and type checks

```sh
make lint
make lint-go
make lint-python
make lint-frontend
```

Go lint runs `gofmt` listing and `go vet`; Python runs Ruff and mypy; frontend runs the configured lint/type-check script. Check the Makefile and Compose runner when a target changes.

## Protobuf generation

Edit `.proto` files under `proto/cryptoscope/v1/`, then run `make proto` to regenerate both language bindings. Include generated outputs when the contract change requires them.

## Conventions

- Go tests live beside packages and use table-driven cases where they clarify parsing or enum behavior.
- Python tests live in each service's `tests/` directory and use pytest with asyncio mode from `pyproject.toml`.
- Frontend tests use Vitest and Testing Library patterns already present in `frontend/src`.
- Prefer in-memory fakes for Go interfaces and assert tenant isolation at service/API boundaries.
- For authorization changes, include both same-tenant success and cross-tenant denial cases.
- For stream and retry changes, cover reconnect, replay, duplicate delivery, and failure recovery.

No test suite was run during the November 15, 2026 documentation review. The roadmap captures code-review findings that need regression tests as part of their fixes.

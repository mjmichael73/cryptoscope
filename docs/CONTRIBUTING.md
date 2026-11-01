# Contributing — cryptoscope

## Getting started

The only host dependency is Docker. Everything else runs inside containers.

```bash
git clone <repo-url> && cd cryptoscope
cp .env.example .env
make up            # start the full stack
make test          # verify everything passes
```

## Development workflow

### 1. Create a branch

```bash
git checkout -b feature/my-change
```

### 2. Make changes and run tests

Tests run via Docker and mount your source as a bind volume — no rebuild needed:

```bash
# Run the specific service you're working on
make test-gateway      # Go gateway changes
make test-query        # Python query-service changes
make test-command      # Python command-service changes

# Run all tests before pushing
make test
```

### 3. Run linters

```bash
make lint              # all linters (Go + Python + frontend)
make lint-go           # just Go: gofmt + go vet
make lint-python       # just Python: ruff + mypy
make lint-frontend     # just frontend: tsc --noEmit
```

### 4. Restart the service to test manually

```bash
make restart svc=api-gateway    # restart a single service
make logs                       # tail all logs
```

## Code conventions

### Go

- Format with `gofmt` (enforced by `make lint-go`)
- Standard layout: `cmd/` for entrypoints, `internal/` for logic
- Use `slog` for structured logging, not `fmt.Println`
- Prefer table-driven tests
- Use in-memory fakes over mocks for interfaces

### Python

- Format with `ruff` (enforced by `make lint-python`)
- Type check with `mypy` (enforced by `make lint-python`)
- Use `structlog` for structured logging, not `print()`
- Services use `pyproject.toml` with `hatchling`
- Tests use `pytest` with `asyncio_mode = "auto"`

### Protobuf

Service contracts live in `proto/cryptoscope/v1/` and are the source of truth. After changing `.proto` files:

```bash
make proto    # regenerate Go and Python stubs
```

### Frontend

- React 19 + TypeScript + Vite + Tailwind CSS
- Run `make lint-frontend` to check types
- All API calls go through `frontend/src/api/client.ts`

## Adding a new Go library

1. Create `libs/go/<name>/` with `go.mod` and source
2. Add tests in the same package
3. Update `docker-compose.tests.yml` — add module to the `test-libs-go` loop
4. Run `make test-libs-go` to verify

## Adding a new Python library

1. Add code under `libs/python/cryptoscope_shared/`
2. Add tests in `libs/python/tests/`
3. Run `make test-libs-python` to verify

## Adding a database migration

```bash
make migrate-new msg="add column_name to table"
# Edit the generated file in migrations/command-service/
make migrate
```

## Commit conventions

- Author: `Mojtaba Michael <mojimich2015@gmail.com>`
- Messages are concise, lowercase, no trailing period
- Start with a verb: add, fix, update, remove, refactor
- Reference issues when applicable

## Pull request process

1. Ensure `make test` and `make lint` pass
2. Update documentation if your change affects the public API or architecture
3. Keep changes feature-scoped — one feature or fix per PR
4. Open a PR against `main`

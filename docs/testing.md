# Testing — cryptoscope

## Overview

All tests run inside Docker containers via `docker-compose.tests.yml`. The only host dependency is Docker. Source code is bind-mounted into test containers, so edits on the host are reflected immediately — no image rebuild needed between runs.

## Test commands

| Command                | What it runs                                    |
| ---------------------- | ----------------------------------------------- |
| `make test`            | All Go + Python tests                           |
| `make test-go`         | All 3 Go services + 8 shared Go libs            |
| `make test-python`     | All 3 Python services + shared Python lib       |
| `make test-ingest`     | ingest-service only                             |
| `make test-processor`  | stream-processor only                           |
| `make test-gateway`    | api-gateway only                                |
| `make test-command`    | command-service only                            |
| `make test-query`      | query-service only                              |
| `make test-alert`      | alert-service only                              |
| `make test-libs-go`    | All 8 Go shared library modules                 |
| `make test-libs-python`| Python shared library tests                     |

## Go tests

Run inside `golang:1.25-alpine` containers. Each service has its own `go.mod` with `replace` directives pointing at the local shared libraries.

```bash
# Run a single service's tests
make test-gateway

# Run all Go tests
make test-go

# Run a specific test by name (via make shell)
make shell-go
cd services/api-gateway
go test ./... -run TestRateLimiter -v -count=1
```

### Conventions

- Table-driven tests for parsing and enum logic
- In-memory fakes over mocks for Go interfaces
- Tests live alongside the code they cover (e.g., `internal/handler/handler_test.go`)
- Run with `-count=1` to disable caching

## Python tests

Run inside pre-built images with `pytest-asyncio` in auto mode. The `Dockerfile.test.python` image caches `pip install ".[dev]"` so containers start in ~0.1s after the first build.

```bash
# Run a single service's tests
make test-query

# Run all Python tests
make test-python

# Run inside a Python dev shell for interactive debugging
make shell-python
cd /app
pytest tests/ -v
```

### Conventions

- All test files are prefixed `test_`
- Use `@pytest.fixture` and `async def` for async fixtures
- `asyncio_mode = "auto"` (configured in each `pyproject.toml`)
- Tests go in a `tests/` directory at the service root

## Frontend lint

TypeScript type-checking via `tsc --noEmit`, run inside `node:22-alpine`:

```bash
make lint-frontend
```

There are no frontend unit tests at this time. The frontend is a thin SPA that delegates all business logic to the backend.

## Linting

| Command            | Tool             | Scope                            |
| ------------------ | ---------------- | -------------------------------- |
| `make lint-go`     | `gofmt` + `go vet` | All Go services + Go libs        |
| `make lint-python` | `ruff` + `mypy`    | All Python services + Python libs|
| `make lint-frontend`| `tsc --noEmit`  | Frontend TypeScript types        |
| `make lint`        | All three above  | Full codebase                    |

## How `docker-compose.tests.yml` works

Every Makefile test command routes through `docker-compose.tests.yml`. Source is mounted as a bind volume:

```yaml
# Example: test-gateway runs this:
image: golang:1.25-alpine
working_dir: /app/services/api-gateway
entrypoint: ["go", "test", "./...", "-count=1"]
volumes:
  - ./proto:/app/proto
  - ./libs:/app/libs
  - ./services:/app/services
  - ./go.work:/app/go.work
```

Python test images are built from `Dockerfile.test.python` with a build arg for the service name. The image is cached after the first build.

## Writing new tests

### Go — add a test for a new handler

```go
// services/ingest-service/internal/handler/tick_test.go
package handler

import (
    "testing"

    "github.com/mojimich2015/cryptoscope/services/ingest-service/internal/domain"
)

func TestProcessTick_ValidationError(t *testing.T) {
    h := NewHandler(nil, nil)
    err := h.ProcessTick(domain.Tick{}) // empty tick
    if err == nil {
        t.Fatal("expected validation error for empty tick")
    }
}
```

### Python — add a test for a new route

```python
# services/query-service/tests/test_candles.py
import pytest
from httpx import AsyncClient
from app.main import create_app

@pytest.fixture
def app():
    return create_app()

async def test_list_candles_returns_empty(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/v1/candles", params={"symbol": "BTC", "interval": "1h"})
    assert resp.status_code == 200
    assert "candles" in resp.json()
```

## CI integration

These same `make test` and `make lint` commands run in CI (`.github/workflows/`). The test containers are ephemeral and leave no state behind.

# Contributor notes

These notes help anyone working in this repository move quickly and keep the
codebase consistent. They apply to the whole tree unless a nested file says
otherwise.

## Layout

- `services/` holds the six microservices. Go services use standard Go module
  layout; Python services use a `src` package layout with `pyproject.toml`.
- `libs/go` and `libs/python` hold shared packages. Prefer extending these over
  copying helpers between services.
- `proto/` is the source of truth for gRPC contracts. Regenerate stubs with
  `make proto` after editing.
- `migrations/` groups database migrations by the owning service.

## Conventions

- Keep changes feature scoped and commit them that way.
- Go code is formatted with `gofmt` and linted with `golangci-lint`.
- Python code is formatted and linted with `ruff` and type checked with `mypy`.
- Log in structured JSON. Do not use plain print statements.
- Every tenant-scoped query must filter by `tenant_id`.
- Write the test alongside the behavior it covers.

## Common commands

```bash
make up          # start the stack
make down        # stop the stack
make test        # run all test suites
make proto       # regenerate protobuf stubs
make lint        # run linters
```

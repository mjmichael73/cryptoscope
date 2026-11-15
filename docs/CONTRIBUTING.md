# Contributing

Keep changes focused and update documentation when behavior or operations change. Do not commit generated secrets, credentials, local data, or build output.

## Workflow

1. Inspect the service boundary, current tests, and related documentation before editing.
2. Make the smallest coherent change and update protobuf bindings if the contract changed (`make proto`).
3. Run the narrowest relevant test or lint target, then broader checks when the change crosses service boundaries.
4. Report commands run and any checks that could not be completed. Do not claim runtime behavior from static inspection alone.
5. Commit only when explicitly requested.

## Code conventions

- Go: format with `gofmt`; keep service internals in their existing module/package structure.
- Python: use the service `src`/`app` package layout, Ruff formatting/lint rules, type annotations, and async patterns.
- Frontend: follow the TypeScript/React patterns in `frontend/src`; preserve accessible labels and keyboard behavior.
- Keep tenant identity explicit in every tenant-scoped operation. Cross-tenant denial belongs in tests.
- Keep API contracts in protobuf where the services communicate through gRPC.
- Use shared logging/config/tracing packages when appropriate. Never log secrets or bearer tokens.

## Repository-specific notes

The environment is designed around Docker Compose. See [development](guides/development.md) and [testing](testing.md) for commands. `make seed` is the demo data command. There is no `make bootstrap` target in the current Makefile.

Current implementation findings are listed in the [roadmap](roadmap.md), including alert tenant-scope issues and data-loss risks. Fixes to those findings should include targeted regression coverage.

## Commit conventions

The repository's contributor notes request concise lowercase commit messages without trailing punctuation. Preserve repository history and author configuration; do not backdate commits unless the user explicitly asks.

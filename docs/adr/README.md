# Architecture decision records

These records preserve the reasons behind selected design choices. They are historical decisions, not proof that every intended property is currently implemented. Where implementation has drifted, use the current architecture docs and roadmap findings as operational truth; add a superseding ADR when a design decision changes.

| ID | Decision | Status |
| --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record significant architecture decisions | Accepted |
| [0002](0002-adopt-a-monorepo.md) | Keep services and contracts in a monorepo | Accepted |
| [0003](0003-split-services-across-go-and-python.md) | Assign languages by service responsibility | Accepted |
| [0004](0004-use-cqrs.md) | Separate command and query paths | Accepted; implementation has exceptions |
| [0005](0005-choose-data-stores-per-workload.md) | Choose storage by data shape | Accepted; actual schemas noted in current docs |
| [0006](0006-multitenancy-row-level.md) | Use row-level tenant identifiers | Accepted; enforcement gaps are tracked |
| [0007](0007-idempotency.md) | Use dedupe and idempotency keys | Accepted; ingestion failure semantics need correction |
| [0008](0008-observability-opentelemetry.md) | Use OpenTelemetry and correlated telemetry | Accepted; actual log backend is Loki configuration |

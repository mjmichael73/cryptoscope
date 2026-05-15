# Architecture Decision Records

This directory captures the significant decisions made while building
cryptoscope. Each record is short, dated, and states the context, the decision,
and the consequences we accepted. The format is intentionally lightweight so
the records stay close to the code and easy to keep current.

| ID   | Title                                             | Status   |
| ---- | ------------------------------------------------- | -------- |
| 0001 | Record architecture decisions                     | Accepted |
| 0002 | Adopt a monorepo for the platform                 | Accepted |
| 0003 | Split services by responsibility across Go and Python | Accepted |
| 0004 | Use CQRS for the read and write paths             | Accepted |
| 0005 | Choose data stores per workload                   | Accepted |
| 0006 | Model multitenancy with row-level tenant_id       | Accepted |
| 0007 | Make ingestion and commands idempotent            | Accepted |
| 0008 | Standardize observability on OpenTelemetry        | Accepted |

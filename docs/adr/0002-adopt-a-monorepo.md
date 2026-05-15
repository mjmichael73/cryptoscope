# 2. Adopt a monorepo for the platform

Date: 2026-05-15

## Status

Accepted

## Context

cryptoscope is six services in two languages that share protobuf contracts and
a set of cross-cutting helpers. I had to choose between one repository per
service and a single repository for the platform.

## Decision

Keep everything in one repository. Shared contracts live in `proto/` and shared
helpers live in `libs/`. Each service keeps its own build, dependencies, and
Dockerfile so it can still be released independently.

## Consequences

Atomic changes across a contract and its consumers become a single commit,
which is the common case here. CI has to be path aware so we only build what
changed. That is a fair trade for the review and refactoring benefits.

# Build the ingest service from the monorepo root context.
FROM golang:1.25-alpine AS build

WORKDIR /src

# Copy the modules the service depends on so the build cache stays warm.
COPY proto ./proto
COPY libs/go ./libs/go
COPY services/ingest-service ./services/ingest-service

WORKDIR /src/services/ingest-service
RUN go env -w GOFLAGS=-mod=mod && \
    CGO_ENABLED=0 GOOS=linux go build -o /out/ingest ./cmd/ingest

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/ingest /usr/local/bin/ingest
USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/ingest"]

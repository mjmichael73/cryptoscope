# Build the stream processor from the monorepo root context.
FROM golang:1.25-alpine AS build

WORKDIR /src

# Copy the modules the service depends on so the build cache stays warm.
COPY proto ./proto
COPY libs/go ./libs/go
COPY services/stream-processor ./services/stream-processor

WORKDIR /src/services/stream-processor
RUN go env -w GOFLAGS=-mod=mod && \
    CGO_ENABLED=0 GOOS=linux go build -o /out/processor ./cmd/processor

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/processor /usr/local/bin/processor
USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/processor"]

# Build the api-gateway service from the monorepo root context.
FROM golang:1.25-alpine AS build

WORKDIR /src

COPY proto ./proto
COPY libs/go ./libs/go
COPY services/api-gateway ./services/api-gateway

WORKDIR /src/services/api-gateway
RUN go env -w GOFLAGS=-mod=mod && \
    CGO_ENABLED=0 GOOS=linux go build -o /out/gateway ./cmd/gateway

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/gateway /usr/local/bin/gateway
USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/gateway"]

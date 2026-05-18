#!/usr/bin/env bash
# Regenerate gRPC stubs for the Go and Python services from the shared protos.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROTO_DIR="$ROOT/proto"
GO_OUT="$ROOT/proto"
PY_OUT="$ROOT/libs/python/cryptoscope_proto"

export PATH="$PATH:$(go env GOPATH)/bin"

echo "==> generating Go stubs"
protoc -I "$PROTO_DIR" \
  --go_out="$GO_OUT" --go_opt=paths=source_relative \
  --go-grpc_out="$GO_OUT" --go-grpc_opt=paths=source_relative \
  "$PROTO_DIR"/cryptoscope/v1/*.proto

echo "==> generating Python stubs"
mkdir -p "$PY_OUT"
python -m grpc_tools.protoc -I "$PROTO_DIR" \
  --python_out="$PY_OUT" \
  --grpc_python_out="$PY_OUT" \
  "$PROTO_DIR"/cryptoscope/v1/*.proto
touch "$PY_OUT/__init__.py"

echo "==> done"

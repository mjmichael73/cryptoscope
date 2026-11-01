# Troubleshooting — cryptoscope

## Common issues

### Docker

**Port already in use**

```bash
# Find what's using the port
lsof -i :8080
# Stop the conflicting process or change the port in docker-compose.yml
```

**Containers won't start**

```bash
# Check logs for the failing service
make logs
# Or check a specific service
docker compose logs api-gateway
docker compose logs command-service
```

**Volumes persisting old state**

```bash
make down        # stops containers and removes volumes
make clean       # removes containers, volumes, images, and build cache
make up          # fresh start
```

**Docker build cache issues**

```bash
docker builder prune -f
make clean
make build
```

### Data stores

**PostgreSQL connection refused**

```bash
# Check if postgres is running and healthy
docker compose ps postgres
docker compose logs postgres

# Verify connectivity
docker compose exec postgres psql -U cryptoscope -d cryptoscope -c "SELECT 1;"
```

**ClickHouse connection refused**

```bash
# Check health
docker compose ps clickhouse

# Verify HTTP interface
curl http://localhost:8123/ping

# Test a query
curl "http://localhost:8123/?query=SELECT+1"
```

**MongoDB authentication failed**

```bash
# Verify credentials match docker-compose.yml
docker compose exec mongo mongosh -u cryptoscope -p cryptoscope --authenticationDatabase admin
```

**Redis connection refused**

```bash
docker compose exec redis redis-cli ping
# Should return PONG
```

**Kafka topic not found**

```bash
# List topics
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Create a topic manually if needed
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic market.ticks.raw --partitions 1 --replication-factor 1
```

### Services

**ingest-service not producing ticks**

```bash
# Check logs for connection errors
docker compose logs ingest-service

# Verify Kafka is reachable from the service
docker compose exec ingest-service sh -c "nc -z kafka 9092"

# Verify exchange APIs are reachable
curl https://api.binance.com/api/v3/ping
curl https://api.exchange.coinbase.com/time
```

**stream-processor not writing candles**

```bash
# Check if ticks are arriving in Kafka
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic market.ticks.raw --from-beginning --max-messages 5

# Check ClickHouse for candles
curl "http://localhost:8123/?query=SELECT+count()+FROM+candles"
```

**query-service returning empty results**

```bash
# Verify ClickHouse has data
curl "http://localhost:8123/?query=SELECT+count()+FROM+candles"

# Check query-service logs
docker compose logs query-service

# Test the API directly
curl http://localhost:8001/v1/candles?symbol=BTC&interval=1h
```

**command-service migration errors**

```bash
# Check current migration state
docker compose exec command-service alembic current

# Apply pending migrations
docker compose exec command-service alembic upgrade head

# Check migration history
docker compose exec command-service alembic history
```

**api-gateway returning 401 in dev mode**

```bash
# Verify DEV_MODE is set
docker compose exec api-gateway env | grep DEV_MODE
# Should show DEV_MODE=true for local dev

# If not, update docker-compose.yml or restart with the correct env
make restart svc=api-gateway
```

### Frontend

**Frontend can't reach the API**

```bash
# Verify the gateway is running
curl http://localhost:8080/healthz

# Check that the Vite proxy is configured (frontend/vite.config.ts)
# /api should proxy to http://localhost:8080
```

**TypeScript errors**

```bash
make lint-frontend
# Fix the errors in frontend/src/
```

### Testing

**Tests fail with "module not found" (Go)**

```bash
# Ensure go.work is at the root and references all modules
cat go.work

# Tidy modules
make shell-go
cd services/api-gateway && go mod tidy
```

**Tests fail with import errors (Python)**

```bash
# Rebuild the test image to pick up new dependencies
docker compose -f docker-compose.tests.yml build test-query
make test-query
```

**Tests pass locally but fail in Docker**

```bash
# Check that the Docker image has the right Python version
docker compose -f docker-compose.tests.yml run --rm test-query python --version

# Run tests verbosely
docker compose -f docker-compose.tests.yml run --rm test-query pytest -v
```

## Getting help

1. Check the logs: `make logs`
2. Run linters: `make lint`
3. Check the [GitHub issues](../../issues)
4. Open a new issue with service logs and steps to reproduce

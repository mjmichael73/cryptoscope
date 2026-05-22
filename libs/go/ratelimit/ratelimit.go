// Package ratelimit implements a Redis backed token bucket.
//
// The gateway needs a limiter that works across replicas, so the state lives in
// Redis rather than in process memory. The refill math runs in a Lua script so
// the read, refill, and take happen atomically.
package ratelimit

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

// script implements a token bucket. KEYS[1] is the bucket key. ARGV are the
// capacity, refill rate per second, current time in milliseconds, and the
// number of tokens requested. It returns 1 when the take succeeds, else 0.
var script = redis.NewScript(`
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call("HMGET", key, "tokens", "ts")
local tokens = tonumber(bucket[1])
local ts = tonumber(bucket[2])
if tokens == nil then
  tokens = capacity
  ts = now
end

local delta = math.max(0, now - ts) / 1000.0
tokens = math.min(capacity, tokens + delta * refill)

local allowed = 0
if tokens >= requested then
  tokens = tokens - requested
  allowed = 1
end

redis.call("HMSET", key, "tokens", tokens, "ts", now)
redis.call("PEXPIRE", key, math.ceil(capacity / refill * 1000))
return allowed
`)

// Limiter enforces a per-key token bucket.
type Limiter struct {
	client   *redis.Client
	capacity int
	refill   float64
}

// New builds a Limiter that allows up to burst tokens with a steady refill of
// requestsPerMinute tokens each minute.
func New(client *redis.Client, requestsPerMinute, burst int) *Limiter {
	return &Limiter{
		client:   client,
		capacity: burst,
		refill:   float64(requestsPerMinute) / 60.0,
	}
}

// Allow reports whether a single request for the given key may proceed.
func (l *Limiter) Allow(ctx context.Context, key string) (bool, error) {
	now := time.Now().UnixMilli()
	res, err := script.Run(ctx, l.client, []string{"ratelimit:" + key},
		l.capacity, l.refill, now, 1).Int()
	if err != nil {
		return false, err
	}
	return res == 1, nil
}

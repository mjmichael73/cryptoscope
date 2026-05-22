// Package idempotency implements deduplication and idempotency-key storage on
// top of Redis.
//
// Our ingestion and command paths are at-least-once, so retries and
// redeliveries are normal. This package turns a key into a cheap "have I
// already handled this" check.
package idempotency

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

// Store records keys that have already been processed.
type Store struct {
	client *redis.Client
	ttl    time.Duration
	prefix string
}

// NewStore builds a Store backed by the given Redis client. Entries expire
// after ttl so the key space does not grow without bound.
func NewStore(client *redis.Client, prefix string, ttl time.Duration) *Store {
	return &Store{client: client, ttl: ttl, prefix: prefix}
}

// FirstSeen atomically records the key and reports whether this is the first
// time we have seen it. A false result means the key was already processed and
// the caller should skip the work.
func (s *Store) FirstSeen(ctx context.Context, key string) (bool, error) {
	ok, err := s.client.SetNX(ctx, s.prefix+":"+key, "1", s.ttl).Result()
	if err != nil {
		return false, err
	}
	return ok, nil
}

// Remember stores a serialized result for an idempotency key so a replay of the
// same command can return the original outcome.
func (s *Store) Remember(ctx context.Context, key, value string) error {
	return s.client.Set(ctx, s.prefix+":result:"+key, value, s.ttl).Err()
}

// Recall returns a previously stored result and whether one existed.
func (s *Store) Recall(ctx context.Context, key string) (string, bool, error) {
	val, err := s.client.Get(ctx, s.prefix+":result:"+key).Result()
	if err == redis.Nil {
		return "", false, nil
	}
	if err != nil {
		return "", false, err
	}
	return val, true, nil
}

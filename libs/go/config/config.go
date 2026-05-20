// Package config loads service configuration from environment variables.
//
// Configuration is intentionally read once at startup and passed explicitly to
// the components that need it. Reading the environment ad hoc from deep in the
// call stack tends to hide dependencies and makes tests awkward, so we avoid it.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Getenv returns the value for key or the provided fallback when it is unset.
func Getenv(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return fallback
}

// GetenvInt reads an integer environment variable with a fallback.
func GetenvInt(key string, fallback int) int {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return fallback
}

// GetenvDuration reads a duration expressed in seconds with a fallback.
func GetenvDuration(key string, fallbackSeconds int) time.Duration {
	return time.Duration(GetenvInt(key, fallbackSeconds)) * time.Second
}

// GetenvList reads a comma separated list, trimming whitespace and skipping
// empty entries.
func GetenvList(key string, fallback []string) []string {
	raw, ok := os.LookupEnv(key)
	if !ok || strings.TrimSpace(raw) == "" {
		return fallback
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		if trimmed := strings.TrimSpace(p); trimmed != "" {
			out = append(out, trimmed)
		}
	}
	return out
}

// MustGetenv returns the value for key or an error when it is missing. Use it
// for values that have no safe default, such as connection strings.
func MustGetenv(key string) (string, error) {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v, nil
	}
	return "", fmt.Errorf("required environment variable %q is not set", key)
}

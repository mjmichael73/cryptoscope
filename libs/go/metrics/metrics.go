// Package metrics exposes a Prometheus registry and a small HTTP server so each
// service can be scraped on a dedicated port.
package metrics

import (
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// Server serves Prometheus metrics over HTTP.
type Server struct {
	Registry *prometheus.Registry
	http     *http.Server
}

// NewServer builds a metrics server listening on addr, for example ":9100".
func NewServer(addr string) *Server {
	registry := prometheus.NewRegistry()
	registry.MustRegister(
		prometheus.NewGoCollector(),
		prometheus.NewProcessCollector(prometheus.ProcessCollectorOpts{}),
	)

	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.HandlerFor(registry, promhttp.HandlerOpts{}))

	return &Server{
		Registry: registry,
		http: &http.Server{
			Addr:              addr,
			Handler:           mux,
			ReadHeaderTimeout: 5 * time.Second,
		},
	}
}

// Start begins serving. It blocks, so callers usually run it in a goroutine.
func (s *Server) Start() error {
	if err := s.http.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}
	return nil
}

// Close stops the metrics server.
func (s *Server) Close() error {
	return s.http.Close()
}

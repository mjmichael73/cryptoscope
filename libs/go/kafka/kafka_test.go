package kafka

import (
	"testing"
)

func TestNewProducer(t *testing.T) {
	p := NewProducer([]string{"localhost:9092"}, "test-topic")
	if p == nil {
		t.Fatal("expected non-nil producer")
	}
	defer p.Close()
}

func TestNewConsumer(t *testing.T) {
	c := NewConsumer([]string{"localhost:9092"}, "test-topic", "test-group")
	if c == nil {
		t.Fatal("expected non-nil consumer")
	}
	defer c.Close()
}

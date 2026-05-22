// Package kafka wraps the segmentio kafka-go client with the small set of
// conveniences the platform needs: JSON envelopes, context aware publish and
// consume, and sane defaults.
package kafka

import (
	"context"
	"encoding/json"
	"time"

	"github.com/segmentio/kafka-go"
)

// Producer publishes JSON encoded messages to a single topic.
type Producer struct {
	writer *kafka.Writer
}

// NewProducer builds a Producer for the given brokers and topic.
func NewProducer(brokers []string, topic string) *Producer {
	return &Producer{
		writer: &kafka.Writer{
			Addr:         kafka.TCP(brokers...),
			Topic:        topic,
			Balancer:     &kafka.Hash{},
			RequiredAcks: kafka.RequireAll,
			BatchTimeout: 50 * time.Millisecond,
		},
	}
}

// Publish encodes value as JSON and writes it under the given key. The key
// drives partitioning, so use a stable key such as the symbol to keep a
// symbol's events in order.
func (p *Producer) Publish(ctx context.Context, key string, value any) error {
	payload, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return p.writer.WriteMessages(ctx, kafka.Message{
		Key:   []byte(key),
		Value: payload,
	})
}

// Close flushes and closes the underlying writer.
func (p *Producer) Close() error {
	return p.writer.Close()
}

// Consumer reads messages from a topic as part of a consumer group.
type Consumer struct {
	reader *kafka.Reader
}

// NewConsumer builds a Consumer joined to the given group.
func NewConsumer(brokers []string, topic, group string) *Consumer {
	return &Consumer{
		reader: kafka.NewReader(kafka.ReaderConfig{
			Brokers:        brokers,
			Topic:          topic,
			GroupID:        group,
			MinBytes:       1,
			MaxBytes:       10 << 20,
			CommitInterval: 0,
		}),
	}
}

// Message pairs the raw payload with the metadata a handler may need.
type Message struct {
	Key   string
	Value []byte
	raw   kafka.Message
}

// Fetch reads the next message without committing its offset. The caller
// commits with Commit once the message is durably handled, which keeps
// processing at-least-once.
func (c *Consumer) Fetch(ctx context.Context) (Message, error) {
	m, err := c.reader.FetchMessage(ctx)
	if err != nil {
		return Message{}, err
	}
	return Message{Key: string(m.Key), Value: m.Value, raw: m}, nil
}

// Commit marks a message as handled.
func (c *Consumer) Commit(ctx context.Context, m Message) error {
	return c.reader.CommitMessages(ctx, m.raw)
}

// Close stops the reader.
func (c *Consumer) Close() error {
	return c.reader.Close()
}

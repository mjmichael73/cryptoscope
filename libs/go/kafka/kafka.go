// Package kafka wraps the segmentio kafka-go client with the small set of
// conveniences the platform needs: JSON envelopes, context aware publish and
// consume, and sane defaults.
package kafka

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/segmentio/kafka-go"
	"github.com/segmentio/kafka-go/sasl"
	"github.com/segmentio/kafka-go/sasl/scram"
)

// ClientConfig describes the Kafka transport security settings shared by
// producers and consumers.
type ClientConfig struct {
	SecurityProtocol string
	SASLMechanism    string
	Username         string
	Password         string
	CAFile           string
}

// LoadClientConfig reads Kafka transport settings from the environment. In
// production, credentials must come from mounted secret files and the broker
// connection must use SASL_SSL.
func LoadClientConfig() (ClientConfig, error) {
	production := strings.EqualFold(strings.TrimSpace(os.Getenv("CRYPTOSCOPE_ENV")), "production")
	protocol := strings.ToUpper(strings.TrimSpace(os.Getenv("KAFKA_SECURITY_PROTOCOL")))
	if protocol == "" {
		protocol = "PLAINTEXT"
	}
	mechanism := strings.ToUpper(strings.TrimSpace(os.Getenv("KAFKA_SASL_MECHANISM")))
	if mechanism == "" {
		mechanism = "SCRAM-SHA-512"
	}
	username, err := kafkaSecret("KAFKA_SASL_USERNAME", production)
	if err != nil {
		return ClientConfig{}, err
	}
	password, err := kafkaSecret("KAFKA_SASL_PASSWORD", production)
	if err != nil {
		return ClientConfig{}, err
	}
	cfg := ClientConfig{
		SecurityProtocol: protocol,
		SASLMechanism:    mechanism,
		Username:         username,
		Password:         password,
		CAFile:           strings.TrimSpace(os.Getenv("KAFKA_TLS_CA_FILE")),
	}
	if production && protocol != "SASL_SSL" {
		return ClientConfig{}, fmt.Errorf("KAFKA_SECURITY_PROTOCOL must be SASL_SSL in production")
	}
	if protocol != "PLAINTEXT" && protocol != "SASL_SSL" {
		return ClientConfig{}, fmt.Errorf("KAFKA_SECURITY_PROTOCOL must be PLAINTEXT or SASL_SSL")
	}
	if protocol == "SASL_SSL" {
		if username == "" || password == "" {
			return ClientConfig{}, fmt.Errorf("Kafka SASL username and password are required for SASL_SSL")
		}
		if mechanism != "SCRAM-SHA-256" && mechanism != "SCRAM-SHA-512" {
			return ClientConfig{}, fmt.Errorf("KAFKA_SASL_MECHANISM must be SCRAM-SHA-256 or SCRAM-SHA-512")
		}
	}
	return cfg, nil
}

func kafkaSecret(name string, production bool) (string, error) {
	path := strings.TrimSpace(os.Getenv(name + "_FILE"))
	if production && path == "" {
		return "", fmt.Errorf("%s_FILE is required in production", name)
	}
	if path != "" {
		b, err := os.ReadFile(path)
		if err != nil {
			return "", fmt.Errorf("read Kafka secret file for %s: %w", name, err)
		}
		value := strings.TrimRight(string(b), "\r\n")
		if value == "" {
			return "", fmt.Errorf("Kafka secret file for %s is empty", name)
		}
		return value, nil
	}
	return strings.TrimSpace(os.Getenv(name)), nil
}

// Transport builds a kafka-go transport with certificate verification enabled.
func (c ClientConfig) Transport() (*kafka.Transport, error) {
	transport := &kafka.Transport{}
	if c.SecurityProtocol == "PLAINTEXT" {
		return transport, nil
	}
	if c.SecurityProtocol != "SASL_SSL" {
		return nil, fmt.Errorf("unsupported Kafka security protocol %q", c.SecurityProtocol)
	}
	tlsConfig := &tls.Config{MinVersion: tls.VersionTLS12}
	if c.CAFile != "" {
		pem, err := os.ReadFile(c.CAFile)
		if err != nil {
			return nil, fmt.Errorf("read Kafka TLS CA file: %w", err)
		}
		roots, err := x509.SystemCertPool()
		if err != nil || roots == nil {
			roots = x509.NewCertPool()
		}
		if ok := roots.AppendCertsFromPEM(pem); !ok {
			return nil, fmt.Errorf("Kafka TLS CA file contains no valid certificates")
		}
		tlsConfig.RootCAs = roots
	}
	var mechanism sasl.Mechanism
	var err error
	switch c.SASLMechanism {
	case "SCRAM-SHA-256":
		mechanism, err = scram.Mechanism(scram.SHA256, c.Username, c.Password)
	case "SCRAM-SHA-512":
		mechanism, err = scram.Mechanism(scram.SHA512, c.Username, c.Password)
	default:
		return nil, fmt.Errorf("unsupported Kafka SASL mechanism %q", c.SASLMechanism)
	}
	if err != nil {
		return nil, fmt.Errorf("configure Kafka SASL mechanism: %w", err)
	}
	transport.TLS = tlsConfig
	transport.SASL = mechanism
	return transport, nil
}

// Producer publishes JSON encoded messages to a single topic.
type Producer struct {
	writer *kafka.Writer
}

// NewProducer builds a Producer for the given brokers and topic.
func NewProducer(brokers []string, topic string) *Producer {
	return NewProducerWithTransport(brokers, topic, nil)
}

// NewProducerWithTransport builds a producer using the supplied transport.
func NewProducerWithTransport(brokers []string, topic string, transport *kafka.Transport) *Producer {
	return &Producer{
		writer: &kafka.Writer{
			Addr:         kafka.TCP(brokers...),
			Topic:        topic,
			Balancer:     &kafka.Hash{},
			RequiredAcks: kafka.RequireAll,
			BatchTimeout: 50 * time.Millisecond,
			Transport:    transport,
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
	return NewConsumerWithTransport(brokers, topic, group, nil)
}

// NewConsumerWithTransport builds a consumer using the supplied transport.
func NewConsumerWithTransport(brokers []string, topic, group string, transport *kafka.Transport) *Consumer {
	return &Consumer{
		reader: kafka.NewReader(kafka.ReaderConfig{
			Brokers:        brokers,
			Topic:          topic,
			GroupID:        group,
			MinBytes:       1,
			MaxBytes:       10 << 20,
			CommitInterval: 0,
			Dialer:         transportDialer(transport),
		}),
	}
}

func transportDialer(transport *kafka.Transport) *kafka.Dialer {
	if transport == nil {
		return nil
	}
	return &kafka.Dialer{TLS: transport.TLS, SASLMechanism: transport.SASL}
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

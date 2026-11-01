package kafka

import (
	"crypto/tls"
	"os"
	"path/filepath"
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

func TestLoadClientConfigRequiresSASLSSLAndSecretFilesInProduction(t *testing.T) {
	t.Setenv("CRYPTOSCOPE_ENV", "production")
	t.Setenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
	t.Setenv("KAFKA_SASL_USERNAME_FILE", "")
	t.Setenv("KAFKA_SASL_PASSWORD_FILE", "")
	if _, err := LoadClientConfig(); err == nil {
		t.Fatal("expected production secret-file validation error")
	}

	t.Setenv("KAFKA_SECURITY_PROTOCOL", "SASL_SSL")
	if _, err := LoadClientConfig(); err == nil {
		t.Fatal("expected missing username secret file error")
	}
}

func TestLoadClientConfigReadsMountedCredentialsAndBuildsVerifiedTLS(t *testing.T) {
	dir := t.TempDir()
	usernameFile := filepath.Join(dir, "username")
	passwordFile := filepath.Join(dir, "password")
	if err := os.WriteFile(usernameFile, []byte("service-user\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(passwordFile, []byte("secret-pass\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CRYPTOSCOPE_ENV", "production")
	t.Setenv("KAFKA_SECURITY_PROTOCOL", "SASL_SSL")
	t.Setenv("KAFKA_SASL_USERNAME_FILE", usernameFile)
	t.Setenv("KAFKA_SASL_PASSWORD_FILE", passwordFile)
	t.Setenv("KAFKA_SASL_MECHANISM", "SCRAM-SHA-512")
	t.Setenv("KAFKA_TLS_CA_FILE", "")

	cfg, err := LoadClientConfig()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Username != "service-user" || cfg.Password != "secret-pass" {
		t.Fatal("mounted Kafka credentials were not loaded")
	}
	transport, err := cfg.Transport()
	if err != nil {
		t.Fatal(err)
	}
	if transport.TLS == nil || transport.TLS.MinVersion != tls.VersionTLS12 || transport.TLS.InsecureSkipVerify {
		t.Fatal("expected TLS 1.2+ with certificate verification enabled")
	}
	if transport.SASL == nil {
		t.Fatal("expected SASL mechanism")
	}
}

func TestTransportRejectsInvalidCAFile(t *testing.T) {
	cfg := ClientConfig{
		SecurityProtocol: "SASL_SSL",
		SASLMechanism:    "SCRAM-SHA-512",
		Username:         "user",
		Password:         "password",
		CAFile:           filepath.Join(t.TempDir(), "bad-ca.pem"),
	}
	if _, err := cfg.Transport(); err == nil {
		t.Fatal("expected invalid CA file error")
	}
}

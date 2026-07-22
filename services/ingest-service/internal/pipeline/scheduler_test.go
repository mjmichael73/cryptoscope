package pipeline

import (
	"context"
	"testing"
	"time"

	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/domain"
	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/source"
)

type fakeSource struct {
	name    string
	fetchFn func(ctx context.Context, symbols []string) ([]domain.Tick, error)
}

func (f *fakeSource) Name() string { return f.name }

func (f *fakeSource) Fetch(ctx context.Context, symbols []string) ([]domain.Tick, error) {
	if f.fetchFn != nil {
		return f.fetchFn(ctx, symbols)
	}
	return nil, nil
}

func TestSchedulerPollOnceFetchesAndProcesses(t *testing.T) {
	src := &fakeSource{
		name: "test-source",
		fetchFn: func(ctx context.Context, symbols []string) ([]domain.Tick, error) {
			return []domain.Tick{
				{Symbol: "BTCUSDT", Price: 50000, Source: "test-source", TsMillis: 1000},
			}, nil
		},
	}
	pub := &fakePublisher{}
	deduper := &fakeDeduper{seen: map[string]bool{}}
	p := New(deduper, pub, testLogger())

	s := NewScheduler([]source.Source{src}, []string{"BTCUSDT"}, 10*time.Millisecond, p, testLogger())

	s.pollOnce(context.Background())
	if len(pub.published) != 1 {
		t.Fatalf("expected 1 published, got %d", len(pub.published))
	}
}

func TestSchedulerPollOnceMultipleSources(t *testing.T) {
	src1 := &fakeSource{
		name: "src1",
		fetchFn: func(ctx context.Context, symbols []string) ([]domain.Tick, error) {
			return []domain.Tick{{Symbol: "BTCUSDT", Price: 50000, Source: "src1", TsMillis: 1000}}, nil
		},
	}
	src2 := &fakeSource{
		name: "src2",
		fetchFn: func(ctx context.Context, symbols []string) ([]domain.Tick, error) {
			return []domain.Tick{{Symbol: "ETHUSDT", Price: 3000, Source: "src2", TsMillis: 1000}}, nil
		},
	}
	pub := &fakePublisher{}
	deduper := &fakeDeduper{seen: map[string]bool{}}
	p := New(deduper, pub, testLogger())

	s := NewScheduler([]source.Source{src1, src2}, []string{"BTCUSDT", "ETHUSDT"}, 10*time.Millisecond, p, testLogger())

	s.pollOnce(context.Background())
	if len(pub.published) != 2 {
		t.Fatalf("expected 2 published, got %d", len(pub.published))
	}
}

func TestSchedulerPollOnceEmptyFetch(t *testing.T) {
	src := &fakeSource{
		name: "empty-source",
		fetchFn: func(ctx context.Context, symbols []string) ([]domain.Tick, error) {
			return nil, nil
		},
	}
	pub := &fakePublisher{}
	deduper := &fakeDeduper{seen: map[string]bool{}}
	p := New(deduper, pub, testLogger())

	s := NewScheduler([]source.Source{src}, []string{"BTCUSDT"}, 10*time.Millisecond, p, testLogger())

	s.pollOnce(context.Background())
	if len(pub.published) != 0 {
		t.Fatalf("expected 0 published, got %d", len(pub.published))
	}
}

func TestSchedulerRunRespectsContextCancel(t *testing.T) {
	src := &fakeSource{
		name: "test-source",
		fetchFn: func(ctx context.Context, symbols []string) ([]domain.Tick, error) {
			return []domain.Tick{{Symbol: "BTCUSDT", Price: 50000, Source: "test-source", TsMillis: 1000}}, nil
		},
	}
	pub := &fakePublisher{}
	deduper := &fakeDeduper{seen: map[string]bool{}}
	p := New(deduper, pub, testLogger())

	s := NewScheduler([]source.Source{src}, []string{"BTCUSDT"}, time.Hour, p, testLogger())

	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	err := s.Run(ctx)
	if err == nil {
		t.Fatal("expected error after context cancel")
	}
}

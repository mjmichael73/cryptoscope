package store

import (
	"context"
	"time"

	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"

	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
)

// MongoArchive stores raw ticks in MongoDB for audit and replay.
type MongoArchive struct {
	collection *mongo.Collection
}

// NewMongoArchive connects to MongoDB and returns an archive writing to the
// ticks collection. It also ensures the collection has a helpful index.
func NewMongoArchive(ctx context.Context, uri, database string) (*MongoArchive, error) {
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		return nil, err
	}
	collection := client.Database(database).Collection("raw_ticks")

	// An index on tenant, symbol, and time keeps audit lookups fast.
	_, err = collection.Indexes().CreateOne(ctx, mongo.IndexModel{
		Keys: primitive.D{
			{Key: "tenant_id", Value: 1},
			{Key: "symbol", Value: 1},
			{Key: "ts_millis", Value: -1},
		},
	})
	if err != nil {
		return nil, err
	}
	return &MongoArchive{collection: collection}, nil
}

type rawTickDoc struct {
	TenantID string    `bson:"tenant_id"`
	Symbol   string    `bson:"symbol"`
	Price    float64   `bson:"price"`
	Volume   float64   `bson:"volume"`
	Source   string    `bson:"source"`
	TsMillis int64     `bson:"ts_millis"`
	StoredAt time.Time `bson:"stored_at"`
}

// SaveTick appends one raw tick to the archive.
func (m *MongoArchive) SaveTick(ctx context.Context, tenantID string, tick domain.Tick) error {
	_, err := m.collection.InsertOne(ctx, rawTickDoc{
		TenantID: tenantID,
		Symbol:   tick.Symbol,
		Price:    tick.Price,
		Volume:   tick.Volume,
		Source:   tick.Source,
		TsMillis: tick.TsMillis,
		StoredAt: time.Now().UTC(),
	})
	return err
}

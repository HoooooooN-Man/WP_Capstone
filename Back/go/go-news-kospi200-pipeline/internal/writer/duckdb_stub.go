package writer

import (
	"context"
	"fmt"

	"github.com/example/go-news-kospi200-pipeline/internal/model"
)

type DuckDBWriter struct {
	DSN string
}

func NewDuckDBWriter(dsn string) *DuckDBWriter {
	return &DuckDBWriter{DSN: dsn}
}

func (w *DuckDBWriter) WriteBatch(_ context.Context, batch model.BatchEnvelope) error {
	return fmt.Errorf("duckdb writer not implemented in this repository skeleton: batch=%s items=%d dsn=%s", batch.BatchID, batch.ItemCount, w.DSN)
}

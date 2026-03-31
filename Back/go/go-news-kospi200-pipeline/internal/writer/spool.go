package writer

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/example/go-news-kospi200-pipeline/internal/model"
)

type SpoolWriter struct {
	baseDir string
}

func NewSpoolWriter(baseDir string) *SpoolWriter {
	return &SpoolWriter{baseDir: baseDir}
}

func (w *SpoolWriter) WriteBatch(_ context.Context, batch model.BatchEnvelope) error {
	if err := os.MkdirAll(w.baseDir, 0o755); err != nil {
		return err
	}
	path := filepath.Join(w.baseDir, fmt.Sprintf("%s.json", batch.BatchID))
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	return enc.Encode(batch)
}

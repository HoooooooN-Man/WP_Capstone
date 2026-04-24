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
	pendingDir := filepath.Join(w.baseDir, "pending")
	doneDir := filepath.Join(w.baseDir, "done")
	failedDir := filepath.Join(w.baseDir, "failed")

	if err := os.MkdirAll(pendingDir, 0o755); err != nil {
		return err
	}
	if err := os.MkdirAll(doneDir, 0o755); err != nil {
		return err
	}
	if err := os.MkdirAll(failedDir, 0o755); err != nil {
		return err
	}

	tmpPath := filepath.Join(pendingDir, fmt.Sprintf("%s.tmp", batch.BatchID))
	finalPath := filepath.Join(pendingDir, fmt.Sprintf("%s.json", batch.BatchID))

	f, err := os.Create(tmpPath)
	if err != nil {
		return err
	}

	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	if err := enc.Encode(batch); err != nil {
		_ = f.Close()
		_ = os.Remove(tmpPath)
		return err
	}

	if err := f.Sync(); err != nil {
		_ = f.Close()
		_ = os.Remove(tmpPath)
		return err
	}

	if err := f.Close(); err != nil {
		_ = os.Remove(tmpPath)
		return err
	}

	if err := os.Rename(tmpPath, finalPath); err != nil {
		_ = os.Remove(tmpPath)
		return err
	}

	return nil
}
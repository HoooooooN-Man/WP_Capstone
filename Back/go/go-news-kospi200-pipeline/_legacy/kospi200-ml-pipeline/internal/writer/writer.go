package writer

import (
	"context"

	"github.com/example/go-news-kospi200-pipeline/internal/model"
)

type BatchWriter interface {
	WriteBatch(ctx context.Context, batch model.BatchEnvelope) error
}

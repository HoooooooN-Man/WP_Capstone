package writer

import (
	"context"
	"log"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/model"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/redis/go-redis/v9"
)

type Service struct {
	cfg    config.Config
	client *redis.Client
	writer BatchWriter
}

func NewService(cfg config.Config, client *redis.Client, writer BatchWriter) *Service {
	return &Service{cfg: cfg, client: client, writer: writer}
}

func (s *Service) Run(ctx context.Context) error {
	if err := redisx.EnsureGroup(ctx, s.client, s.cfg.BatchReadyStream, s.cfg.BatchGroup); err != nil {
		return err
	}
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		msgs, err := redisx.ReadGroup(ctx, s.client, s.cfg.BatchGroup, s.cfg.BatchConsumer, s.cfg.BatchReadyStream, s.cfg.PollBlock, 5)
		if err != nil {
			return err
		}
		if len(msgs) == 0 {
			continue
		}
		for _, msg := range msgs {
			batch, err := redisx.ParsePayload[model.BatchEnvelope](msg)
			if err != nil {
				log.Printf("writer: parse error: %v", err)
				_ = redisx.Ack(ctx, s.client, s.cfg.BatchReadyStream, s.cfg.BatchGroup, msg.ID)
				continue
			}
			if err := s.writer.WriteBatch(ctx, batch); err != nil {
				return err
			}
			if err := redisx.Ack(ctx, s.client, s.cfg.BatchReadyStream, s.cfg.BatchGroup, msg.ID); err != nil {
				return err
			}
			log.Printf("writer: wrote batch=%s items=%d", batch.BatchID, batch.ItemCount)
		}
	}
}

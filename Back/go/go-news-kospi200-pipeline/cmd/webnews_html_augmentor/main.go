package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	baseconfig "github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	webconfig "github.com/example/go-news-kospi200-pipeline/internal/webnews/config"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/htmlaugment"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/redis/go-redis/v9"
)

const htmlAugmentGroupName = "html-augment-group"

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	baseCfg := baseconfig.Load()

	webCfg, err := webconfig.LoadFromEnv()
	if err != nil {
		log.Fatalf("webnews_html_augmentor: load env failed: %v", err)
	}

	client := redisx.NewClient(baseCfg)

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	if err := redisx.Ping(pingCtx, client); err != nil {
		cancel()
		log.Fatalf("webnews_html_augmentor: redis ping failed addr=%s err=%v", baseCfg.RedisAddr, err)
	}
	cancel()

	if err := ensureHTMLAugmentGroup(ctx, client, webCfg.RedisPrefix); err != nil {
		log.Fatalf("webnews_html_augmentor: ensure group failed: %v", err)
	}

	consumerName := hostnameOr("webnews-html-augmentor-1")
	fetcher := htmlaugment.NewFetcher(webCfg.FetchTimeout, webCfg.UserAgent)

	log.Printf(
		"webnews_html_augmentor: start redis=%s stream=%s consumer=%s",
		baseCfg.RedisAddr,
		streamCollectJobs(webCfg.RedisPrefix),
		consumerName,
	)

	for {
		select {
		case <-ctx.Done():
			log.Printf("webnews_html_augmentor: shutdown requested")
			return
		default:
		}

		messages, err := readHTMLAugmentJobs(
			ctx,
			client,
			webCfg.RedisPrefix,
			consumerName,
			6,
			baseCfg.PollBlock,
		)
		if err != nil {
			if errors.Is(err, context.Canceled) {
				return
			}
			log.Printf("webnews_html_augmentor: read jobs error: %v", err)
			time.Sleep(2 * time.Second)
			continue
		}

		if len(messages) == 0 {
			continue
		}

		for _, msg := range messages {
			job, err := parseCollectJob(msg)
			if err != nil {
				log.Printf("webnews_html_augmentor: parse job failed msg_id=%s err=%v", msg.ID, err)
				_ = ackHTMLAugmentJob(ctx, client, webCfg.RedisPrefix, msg.ID)
				continue
			}

			if strings.TrimSpace(job.Query) == "" {
				log.Printf("webnews_html_augmentor: empty query msg_id=%s category=%s", msg.ID, job.CategoryID)
				_ = ackHTMLAugmentJob(ctx, client, webCfg.RedisPrefix, msg.ID)
				continue
			}

			htmlText, finalURL, err := fetcher.FetchSearchHTML(ctx, job.Query)
			if err != nil {
				log.Printf("webnews_html_augmentor: fetch html failed msg_id=%s category=%s err=%v", msg.ID, job.CategoryID, err)
				continue
			}

			cards, err := htmlaugment.ParseCardsFromSearchHTML(
				htmlText,
				finalURL,
				job.DisplayDate,
				job.CategoryID,
				job.CategoryLabel,
				job.Query,
				job.TopN,
			)
			if err != nil {
				log.Printf("webnews_html_augmentor: parse cards failed msg_id=%s category=%s err=%v", msg.ID, job.CategoryID, err)
				continue
			}

			if err := enqueueHTMLCards(ctx, client, webCfg.RedisPrefix, cards); err != nil {
				log.Printf("webnews_html_augmentor: enqueue cards failed msg_id=%s category=%s err=%v", msg.ID, job.CategoryID, err)
				continue
			}

			if err := ackHTMLAugmentJob(ctx, client, webCfg.RedisPrefix, msg.ID); err != nil {
				log.Printf("webnews_html_augmentor: ack failed msg_id=%s err=%v", msg.ID, err)
				continue
			}

			log.Printf(
				"webnews_html_augmentor: augmented msg_id=%s category=%s cards=%d query=%q",
				msg.ID,
				job.CategoryID,
				len(cards),
				job.Query,
			)
		}
	}
}

func ensureHTMLAugmentGroup(ctx context.Context, client *redis.Client, prefix string) error {
	err := client.XGroupCreateMkStream(ctx, streamCollectJobs(prefix), htmlAugmentGroupName, "0").Err()
	if err != nil && !strings.Contains(err.Error(), "BUSYGROUP") {
		return fmt.Errorf("create html augment group: %w", err)
	}
	return nil
}

func readHTMLAugmentJobs(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	consumer string,
	count int64,
	block time.Duration,
) ([]redis.XMessage, error) {
	pending, err := readHTMLAugmentJobsByID(ctx, client, prefix, consumer, count, 0, "0")
	if err != nil {
		return nil, err
	}
	if len(pending) > 0 {
		return pending, nil
	}

	return readHTMLAugmentJobsByID(ctx, client, prefix, consumer, count, block, ">")
}

func readHTMLAugmentJobsByID(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	consumer string,
	count int64,
	block time.Duration,
	streamID string,
) ([]redis.XMessage, error) {
	streams, err := client.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    htmlAugmentGroupName,
		Consumer: consumer,
		Streams:  []string{streamCollectJobs(prefix), streamID},
		Count:    count,
		Block:    block,
	}).Result()

	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("read html augment jobs: %w", err)
	}
	if len(streams) == 0 {
		return nil, nil
	}

	return streams[0].Messages, nil
}

func parseCollectJob(msg redis.XMessage) (model.CollectJob, error) {
	get := func(key string) string {
		if v, ok := msg.Values[key]; ok {
			return strings.TrimSpace(fmt.Sprint(v))
		}
		return ""
	}

	topN := 10
	if raw := get("top_n"); raw != "" {
		v, err := strconv.Atoi(raw)
		if err != nil {
			return model.CollectJob{}, fmt.Errorf("invalid top_n: %w", err)
		}
		topN = v
	}

	job := model.CollectJob{
		DisplayDate:   get("display_date"),
		CategoryID:    get("category_id"),
		CategoryLabel: get("category_label"),
		Mode:          get("mode"),
		Source:        get("source"),
		FeedURL:       get("feed_url"),
		Query:         get("query"),
		TopN:          topN,
		ScheduledAt:   get("scheduled_at"),
		WindowStart:   get("window_start"),
		WindowEnd:     get("window_end"),
	}

	if job.DisplayDate == "" || job.CategoryID == "" {
		return model.CollectJob{}, fmt.Errorf("missing required job fields msg_id=%s", msg.ID)
	}
	if job.CategoryLabel == "" {
		job.CategoryLabel = job.CategoryID
	}
	if job.Source == "" {
		job.Source = "google_news"
	}

	return job, nil
}

func ackHTMLAugmentJob(ctx context.Context, client *redis.Client, prefix string, msgID string) error {
	if err := client.XAck(ctx, streamCollectJobs(prefix), htmlAugmentGroupName, msgID).Err(); err != nil {
		return fmt.Errorf("ack html augment job: %w", err)
	}
	return nil
}

func enqueueHTMLCards(ctx context.Context, client *redis.Client, prefix string, cards []model.HTMLNewsCard) error {
	for _, card := range cards {
		if _, err := client.XAdd(ctx, &redis.XAddArgs{
			Stream: streamHTMLAugmented(prefix),
			Values: map[string]any{
				"display_date":    card.DisplayDate,
				"category_id":     card.CategoryID,
				"category_label":  card.CategoryLabel,
				"card_rank":       strconv.Itoa(card.CardRank),
				"title":           card.Title,
				"publisher":       card.Publisher,
				"google_news_url": card.GoogleNewsURL,
				"possible_url":    card.PossibleURL,
				"thumbnail_url":   card.ThumbnailURL,
				"collected_at":    card.CollectedAt,
				"query":           card.Query,
				"source":          card.Source,
			},
		}).Result(); err != nil {
			return fmt.Errorf("xadd html augmented card: %w", err)
		}
	}
	return nil
}

func streamCollectJobs(prefix string) string {
	return fmt.Sprintf("%s:collect_jobs", prefix)
}

func streamHTMLAugmented(prefix string) string {
	return fmt.Sprintf("%s:html_augmented", prefix)
}

func hostnameOr(fallback string) string {
	name, err := os.Hostname()
	if err != nil || name == "" {
		return fallback
	}
	return name
}

package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	baseconfig "github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	webconfig "github.com/example/go-news-kospi200-pipeline/internal/webnews/config"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/publisher"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/redisstore"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/timewindow"
)

func main() {
	phase := flag.String("phase", "after", "prune phase: before or after")
	displayDateFlag := flag.String("display-date", "", "target display date in YYYY-MM-DD")
	trimPublishEvents := flag.Int64("trim-publish-events", 30, "max publish events to keep; set 0 to delete publish event stream")
	deleteCurrentStaging := flag.Bool("delete-current-staging", true, "delete staging directory for the target display date")
	resetDisplayDate := flag.Bool("reset-display-date", false, "delete rank/item/seen/lock keys for the target display date before running the batch")
	flag.Parse()

	baseCfg := baseconfig.Load()

	webCfg, err := webconfig.LoadFromEnv()
	if err != nil {
		log.Fatalf("webnews_prune: load env failed: %v", err)
	}

	if err := webconfig.EnsureDataDirs(webCfg.DataDir); err != nil {
		log.Fatalf("webnews_prune: ensure data dirs failed: %v", err)
	}

	loc, err := webconfig.LoadLocation(webCfg.Timezone)
	if err != nil {
		log.Fatalf("webnews_prune: load timezone failed: %v", err)
	}

	displayDate := *displayDateFlag
	if displayDate == "" {
		now := time.Now().In(loc)
		displayDate, _, _ = timewindow.Resolve(now, loc, webCfg.MarketOpenHour, webCfg.MarketOpenMinute)
	}

	client := redisx.NewClient(baseCfg)

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	if err := redisx.Ping(ctx, client); err != nil {
		log.Fatalf("webnews_prune: redis ping failed addr=%s err=%v", baseCfg.RedisAddr, err)
	}

	result := pruneResult{
		Phase:       *phase,
		DisplayDate: displayDate,
	}

	switch *phase {
	case "before":
		deletedTransientKeys, err := redisstore.DeleteTransientStreams(ctx, client, webCfg.RedisPrefix, true)
		if err != nil {
			log.Fatalf("webnews_prune: delete transient streams failed: %v", err)
		}
		result.DeletedTransientKeys = deletedTransientKeys

		if *resetDisplayDate {
			deletedDisplayDateKeys, err := redisstore.DeleteDateScopedKeys(
				ctx,
				client,
				webCfg.RedisPrefix,
				displayDate,
			)
			if err != nil {
				log.Fatalf("webnews_prune: reset display date keys failed: %v", err)
			}
			result.DeletedDisplayDateKeys = deletedDisplayDateKeys
		}

		removedStagingDirs, err := cleanupStagingDirs(webCfg.DataDir, displayDate, *deleteCurrentStaging)
		if err != nil {
			log.Fatalf("webnews_prune: cleanup staging failed: %v", err)
		}
		result.RemovedStagingDirs = removedStagingDirs

	case "after":
		deletedTransientKeys, err := redisstore.DeleteTransientStreams(ctx, client, webCfg.RedisPrefix, false)
		if err != nil {
			log.Fatalf("webnews_prune: delete transient streams failed: %v", err)
		}
		result.DeletedTransientKeys = deletedTransientKeys

		publishEventsLen, err := redisstore.TrimPublishEvents(ctx, client, webCfg.RedisPrefix, *trimPublishEvents)
		if err != nil {
			log.Fatalf("webnews_prune: trim publish events failed: %v", err)
		}
		result.PublishEventsLen = publishEventsLen

		deletedOldDateKeys, err := redisstore.DeleteDateScopedKeysExcept(ctx, client, webCfg.RedisPrefix, displayDate)
		if err != nil {
			log.Fatalf("webnews_prune: delete old date scoped keys failed: %v", err)
		}
		result.DeletedOldDateKeys = deletedOldDateKeys

		removedStagingDirs, err := cleanupStagingDirs(webCfg.DataDir, displayDate, *deleteCurrentStaging)
		if err != nil {
			log.Fatalf("webnews_prune: cleanup staging failed: %v", err)
		}
		result.RemovedStagingDirs = removedStagingDirs

		archiveRoot := filepath.Join(webCfg.DataDir, "archive")
		if err := publisher.CleanupArchiveDirs(archiveRoot, webCfg.KeepLastGood); err != nil {
			log.Fatalf("webnews_prune: cleanup archive failed: %v", err)
		}

	default:
		log.Fatalf("webnews_prune: invalid phase=%q; expected before or after", *phase)
	}

	log.Printf(
		"webnews_prune: done phase=%s display_date=%s deleted_transient_keys=%d deleted_display_date_keys=%d deleted_old_date_keys=%d publish_events_len=%d removed_staging_dirs=%d",
		result.Phase,
		result.DisplayDate,
		result.DeletedTransientKeys,
		result.DeletedDisplayDateKeys,
		result.DeletedOldDateKeys,
		result.PublishEventsLen,
		result.RemovedStagingDirs,
	)
}

type pruneResult struct {
	Phase                  string
	DisplayDate            string
	DeletedTransientKeys   int
	DeletedDisplayDateKeys int
	DeletedOldDateKeys     int
	PublishEventsLen       int64
	RemovedStagingDirs     int
}

func cleanupStagingDirs(dataDir string, displayDate string, deleteCurrent bool) (int, error) {
	stagingRoot := filepath.Join(dataDir, "staging")

	if err := os.MkdirAll(stagingRoot, 0o755); err != nil {
		return 0, fmt.Errorf("mkdir staging root: %w", err)
	}

	entries, err := os.ReadDir(stagingRoot)
	if err != nil {
		return 0, fmt.Errorf("read staging root: %w", err)
	}

	removed := 0

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		if !deleteCurrent && entry.Name() == displayDate {
			continue
		}

		path := filepath.Join(stagingRoot, entry.Name())
		if err := os.RemoveAll(path); err != nil {
			return removed, fmt.Errorf("remove staging dir %s: %w", path, err)
		}

		removed++
	}

	return removed, nil
}

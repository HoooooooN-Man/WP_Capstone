package main

import (
	"context"
	"flag"
	"log"
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
	displayDateFlag := flag.String("display-date", "", "target display date in YYYY-MM-DD")
	flag.Parse()

	baseCfg := baseconfig.Load()

	webCfg, err := webconfig.LoadFromEnv()
	if err != nil {
		log.Fatalf("webnews_publish: load env failed: %v", err)
	}

	if err := webconfig.EnsureDataDirs(webCfg.DataDir); err != nil {
		log.Fatalf("webnews_publish: ensure data dirs failed: %v", err)
	}

	loc, err := webconfig.LoadLocation(webCfg.Timezone)
	if err != nil {
		log.Fatalf("webnews_publish: load timezone failed: %v", err)
	}

	categories, err := webconfig.LoadCategories(webCfg.CategoriesFile, webCfg.TopN)
	if err != nil {
		log.Fatalf("webnews_publish: load categories failed: %v", err)
	}

	displayDate := *displayDateFlag
	if displayDate == "" {
		now := time.Now().In(loc)
		displayDate, _, _ = timewindow.Resolve(now, loc, webCfg.MarketOpenHour, webCfg.MarketOpenMinute)
	}

	expectedCategoryIDs := make([]string, 0, len(categories))
	for _, c := range categories {
		expectedCategoryIDs = append(expectedCategoryIDs, c.ID)
	}

	stagingDir := filepath.Join(webCfg.DataDir, "staging", displayDate)
	manifest, err := publisher.LoadAndValidateStaging(stagingDir, displayDate, expectedCategoryIDs)
	if err != nil {
		log.Fatalf("webnews_publish: staging validation failed: %v", err)
	}

	client := redisx.NewClient(baseCfg)

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	if err := redisx.Ping(ctx, client); err != nil {
		log.Fatalf("webnews_publish: redis ping failed addr=%s err=%v", baseCfg.RedisAddr, err)
	}

	swapResult, err := publisher.PublishStagingToCurrent(webCfg.DataDir, displayDate, webCfg.KeepLastGood)
	if err != nil {
		log.Fatalf("webnews_publish: publish swap failed: %v", err)
	}

	if err := redisstore.SetCurrentManifest(ctx, client, webCfg.RedisPrefix, manifest, swapResult.CurrentDir); err != nil {
		log.Fatalf("webnews_publish: set current manifest failed: %v", err)
	}

	if err := redisstore.AddPublishEvent(ctx, client, webCfg.RedisPrefix, displayDate, swapResult.CurrentDir); err != nil {
		log.Fatalf("webnews_publish: add publish event failed: %v", err)
	}

	deletedKeys, err := redisstore.DeleteDateScopedKeysExcept(ctx, client, webCfg.RedisPrefix, displayDate)
	if err != nil {
		log.Fatalf("webnews_publish: delete old redis keys failed: %v", err)
	}

	archiveRoot := filepath.Join(webCfg.DataDir, "archive")
	if err := publisher.CleanupArchiveDirs(archiveRoot, webCfg.KeepLastGood); err != nil {
		log.Fatalf("webnews_publish: cleanup archive failed: %v", err)
	}

	log.Printf(
		"webnews_publish: done display_date=%s current_dir=%s backup_dir=%s deleted_keys=%d keep_last_good=%t",
		displayDate,
		swapResult.CurrentDir,
		swapResult.BackupDir,
		deletedKeys,
		webCfg.KeepLastGood,
	)
}

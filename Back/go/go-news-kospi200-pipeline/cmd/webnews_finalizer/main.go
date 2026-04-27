package main

import (
	"context"
	"flag"
	"log"
	"os"
	"path/filepath"
	"time"

	baseconfig "github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	webconfig "github.com/example/go-news-kospi200-pipeline/internal/webnews/config"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/fileout"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/redisstore"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/timewindow"
)

func main() {
	displayDateFlag := flag.String("display-date", "", "target display date in YYYY-MM-DD")
	flag.Parse()

	baseCfg := baseconfig.Load()

	webCfg, err := webconfig.LoadFromEnv()
	if err != nil {
		log.Fatalf("webnews_finalizer: load env failed: %v", err)
	}

	if err := webconfig.EnsureDataDirs(webCfg.DataDir); err != nil {
		log.Fatalf("webnews_finalizer: ensure data dirs failed: %v", err)
	}

	loc, err := webconfig.LoadLocation(webCfg.Timezone)
	if err != nil {
		log.Fatalf("webnews_finalizer: load timezone failed: %v", err)
	}

	categories, err := webconfig.LoadCategories(webCfg.CategoriesFile, webCfg.TopN)
	if err != nil {
		log.Fatalf("webnews_finalizer: load categories failed: %v", err)
	}

	displayDate := *displayDateFlag
	if displayDate == "" {
		now := time.Now().In(loc)
		displayDate, _, _ = timewindow.Resolve(now, loc, webCfg.MarketOpenHour, webCfg.MarketOpenMinute)
	}

	windowStart, windowEnd, err := timewindow.WindowForDisplayDate(
		displayDate,
		loc,
		webCfg.MarketOpenHour,
		webCfg.MarketOpenMinute,
	)
	if err != nil {
		log.Fatalf("webnews_finalizer: resolve window failed: %v", err)
	}

	client := redisx.NewClient(baseCfg)

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	if err := redisx.Ping(ctx, client); err != nil {
		log.Fatalf("webnews_finalizer: redis ping failed addr=%s err=%v", baseCfg.RedisAddr, err)
	}

	generatedAt := time.Now().In(loc).Format(time.RFC3339)
	stagingDir := filepath.Join(webCfg.DataDir, "staging", displayDate)

	if err := os.RemoveAll(stagingDir); err != nil {
		log.Fatalf("webnews_finalizer: remove old staging dir failed: %v", err)
	}
	if err := os.MkdirAll(stagingDir, 0o755); err != nil {
		log.Fatalf("webnews_finalizer: create staging dir failed: %v", err)
	}

	categoryIDs := make([]string, 0, len(categories))

	for _, category := range categories {
		topN := category.TopN
		if topN <= 0 {
			topN = webCfg.TopN
		}
		if topN <= 0 {
			topN = 10
		}

		itemIDs, err := redisstore.TopRankedItemIDs(
			ctx,
			client,
			webCfg.RedisPrefix,
			displayDate,
			category.ID,
			int64(topN),
		)
		if err != nil {
			log.Fatalf("webnews_finalizer: read top ranked item ids failed category=%s err=%v", category.ID, err)
		}

		items := make([]model.FinalizedNewsCard, 0, len(itemIDs))

		for idx, itemID := range itemIDs {
			enrichedItem, err := redisstore.GetEnrichedItem(
				ctx,
				client,
				webCfg.RedisPrefix,
				displayDate,
				itemID,
			)
			if err != nil {
				log.Printf(
					"webnews_finalizer: skip missing item category=%s item_id=%s err=%v",
					category.ID,
					itemID,
					err,
				)
				continue
			}

			items = append(items, model.FinalizedNewsCard{
				Rank: idx + 1,

				ID: enrichedItem.ID,

				Title:         enrichedItem.Title,
				Publisher:     enrichedItem.Publisher,
				GoogleNewsURL: enrichedItem.GoogleNewsURL,
				OriginURL:     enrichedItem.OriginURL,
				CanonicalURL:  enrichedItem.CanonicalURL,
				ImageURL:      enrichedItem.ImageURL,

				PublishedAt: enrichedItem.PublishedAt,
				CollectedAt: enrichedItem.CollectedAt,
				FirstSeenAt: enrichedItem.FirstSeenAt,
				LastSeenAt:  enrichedItem.LastSeenAt,

				SeenCount:  enrichedItem.SeenCount,
				BestRank:   enrichedItem.BestRank,
				LatestRank: enrichedItem.LatestRank,
				Score:      enrichedItem.Score,

				Source: enrichedItem.Source,
				Query:  enrichedItem.Query,
			})
		}

		categoryFile := model.FinalizedCategoryFile{
			DisplayDate:   displayDate,
			CategoryID:    category.ID,
			CategoryLabel: category.Label,
			WindowStart:   windowStart.Format(time.RFC3339),
			WindowEnd:     windowEnd.Format(time.RFC3339),
			GeneratedAt:   generatedAt,
			ItemCount:     len(items),
			Items:         items,
		}

		outPath := filepath.Join(stagingDir, category.ID+".json")
		if err := fileout.WriteJSON(outPath, categoryFile); err != nil {
			log.Fatalf(
				"webnews_finalizer: write category file failed category=%s path=%s err=%v",
				category.ID,
				outPath,
				err,
			)
		}

		categoryIDs = append(categoryIDs, category.ID)

		log.Printf(
			"webnews_finalizer: wrote category=%s items=%d path=%s",
			category.ID,
			len(items),
			outPath,
		)
	}

	manifest := model.FinalizeManifest{
		DisplayDate: displayDate,
		WindowStart: windowStart.Format(time.RFC3339),
		WindowEnd:   windowEnd.Format(time.RFC3339),
		GeneratedAt: generatedAt,
		Categories:  categoryIDs,
		TopN:        webCfg.TopN,
	}

	manifestPath := filepath.Join(stagingDir, "manifest.json")
	if err := fileout.WriteJSON(manifestPath, manifest); err != nil {
		log.Fatalf("webnews_finalizer: write manifest failed path=%s err=%v", manifestPath, err)
	}

	log.Printf(
		"webnews_finalizer: done display_date=%s staging_dir=%s categories=%d",
		displayDate,
		stagingDir,
		len(categoryIDs),
	)
}

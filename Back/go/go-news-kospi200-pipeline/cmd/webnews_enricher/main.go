package main

import (
	"context"
	"errors"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	baseconfig "github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/config"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/enricher"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/htmlaugment"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/redisstore"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	baseCfg := baseconfig.Load()

	webCfg, err := config.LoadFromEnv()
	if err != nil {
		log.Fatalf("webnews_enricher: load env failed: %v", err)
	}

	client := redisx.NewClient(baseCfg)

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	if err := redisx.Ping(pingCtx, client); err != nil {
		cancel()
		log.Fatalf("webnews_enricher: redis ping failed addr=%s err=%v", baseCfg.RedisAddr, err)
	}
	cancel()

	if err := redisstore.EnsureRawGroup(ctx, client, webCfg.RedisPrefix); err != nil {
		log.Fatalf("webnews_enricher: ensure raw group failed: %v", err)
	}

	consumerName := hostnameOr("webnews-enricher-1")
	resolver := enricher.NewOriginResolver(webCfg.FetchTimeout, webCfg.UserAgent)
	metaFetcher := enricher.NewMetaFetcher(webCfg.FetchTimeout, webCfg.UserAgent)

	log.Printf(
		"webnews_enricher: start redis=%s stream=%s consumer=%s",
		baseCfg.RedisAddr,
		redisstore.StreamRawItems(webCfg.RedisPrefix),
		consumerName,
	)

	for {
		select {
		case <-ctx.Done():
			log.Printf("webnews_enricher: shutdown requested")
			return
		default:
		}

		messages, err := redisstore.ReadRawItems(
			ctx,
			client,
			webCfg.RedisPrefix,
			consumerName,
			10,
			baseCfg.PollBlock,
		)
		if err != nil {
			if errors.Is(err, context.Canceled) {
				return
			}
			log.Printf("webnews_enricher: read raw items error: %v", err)
			time.Sleep(2 * time.Second)
			continue
		}

		if len(messages) == 0 {
			continue
		}

		for _, msg := range messages {
			rawItem, err := redisstore.ParseRawItem(msg)
			if err != nil {
				log.Printf("webnews_enricher: parse raw item failed msg_id=%s err=%v", msg.ID, err)
				_ = redisstore.AckRawItem(ctx, client, webCfg.RedisPrefix, msg.ID)
				continue
			}

			htmlCards, err := redisstore.ReadRecentHTMLCards(
				ctx,
				client,
				webCfg.RedisPrefix,
				rawItem.DisplayDate,
				rawItem.CategoryID,
				rawItem.Query,
				300,
			)
			if err != nil {
				log.Printf("webnews_enricher: read recent html cards failed msg_id=%s category=%s err=%v", msg.ID, rawItem.CategoryID, err)
			}

			matchResult := htmlaugment.FindBestHTMLCard(rawItem, htmlCards)

			enrichedItem, err := enrichOne(ctx, resolver, metaFetcher, rawItem, matchResult.Card)
			if err != nil {
				log.Printf("webnews_enricher: enrich failed msg_id=%s category=%s err=%v", msg.ID, rawItem.CategoryID, err)
				continue
			}

			scoreDelta := redisstore.ScoreDelta(
				enrichedItem.LatestRank,
				enrichedItem.ImageURL,
				enrichedItem.OriginURL,
				enrichedItem.GoogleNewsURL,
			)

			score, err := redisstore.AddRankScore(
				ctx,
				client,
				webCfg.RedisPrefix,
				enrichedItem.DisplayDate,
				enrichedItem.CategoryID,
				enrichedItem.ID,
				scoreDelta,
			)
			if err != nil {
				log.Printf("webnews_enricher: add rank score failed msg_id=%s item_id=%s err=%v", msg.ID, enrichedItem.ID, err)
				continue
			}
			enrichedItem.Score = score

			storedItem, err := redisstore.UpsertEnrichedItem(ctx, client, webCfg.RedisPrefix, enrichedItem)
			if err != nil {
				log.Printf("webnews_enricher: upsert enriched item failed msg_id=%s item_id=%s err=%v", msg.ID, enrichedItem.ID, err)
				continue
			}

			if err := redisstore.AckRawItem(ctx, client, webCfg.RedisPrefix, msg.ID); err != nil {
				log.Printf("webnews_enricher: ack raw item failed msg_id=%s err=%v", msg.ID, err)
				continue
			}

			matchScore := 0
			if matchResult.Card != nil {
				matchScore = matchResult.Score
			}

			log.Printf(
				"webnews_enricher: stored msg_id=%s category=%s item_id=%s seen=%d score=%.2f image=%t link_source=%s image_source=%s html_match_score=%d",
				msg.ID,
				storedItem.CategoryID,
				storedItem.ID,
				storedItem.SeenCount,
				storedItem.Score,
				strings.TrimSpace(storedItem.ImageURL) != "",
				enrichedItem.LinkSource,
				enrichedItem.ImageSource,
				matchScore,
			)
		}
	}
}

func enrichOne(
	ctx context.Context,
	resolver *enricher.OriginResolver,
	metaFetcher *enricher.MetaFetcher,
	raw model.RawNewsItem,
	matchedCard *model.HTMLNewsCard,
) (model.EnrichedNewsItem, error) {
	now := time.Now().Format(time.RFC3339)

	publisher := choosePublisher(raw.Publisher, matchedCard)

	originURL := ""
	linkSource := ""

	// 1) HTML 보강 링크 후보 우선
	if matchedCard != nil {
		if candidate := strings.TrimSpace(matchedCard.PossibleURL); candidate != "" && !enricher.IsBlockedOriginCandidateURL(candidate) {
			originURL = candidate
			linkSource = "html_possible_url"
		}
	}

	// 2) 없으면 resolver 시도 (단, Google/gstatic 후보는 버림)
	if strings.TrimSpace(originURL) == "" {
		if resolved, err := resolver.ResolveOriginURL(ctx, raw.GoogleNewsURL); err == nil {
			resolved = strings.TrimSpace(resolved)
			if resolved != "" && !enricher.IsBlockedOriginCandidateURL(resolved) {
				originURL = resolved
				linkSource = "resolver"
			}
		}
	}

	// 3) 그래도 없으면 Google News fallback
	if strings.TrimSpace(originURL) == "" {
		originURL = strings.TrimSpace(raw.GoogleNewsURL)
		linkSource = "google_news_fallback"
	}

	meta := enricher.PageMeta{}

	// 실제 외부 origin일 때만 meta fetch
	if strings.TrimSpace(originURL) != "" &&
		!enricher.IsBlockedOriginCandidateURL(originURL) &&
		!enricher.IsGoogleNewsLikeURL(originURL) {
		if fetchedMeta, err := metaFetcher.FetchMeta(ctx, originURL); err == nil {
			meta = fetchedMeta
		}
	}

	canonicalURL := enricher.ChoosePreferredCanonicalURL(
		meta.CanonicalURL,
		originURL,
	)

	itemID := enricher.BuildItemID(canonicalURL, raw.Title, publisher)
	publishedAt := firstNonEmpty(raw.PublishedAt, meta.PublishedAt)

	imageURL := ""
	imageSource := ""

	switch {
	case strings.TrimSpace(meta.ImageURL) != "":
		imageURL = strings.TrimSpace(meta.ImageURL)
		imageSource = "og:image"
	case matchedCard != nil && strings.TrimSpace(matchedCard.ThumbnailURL) != "":
		imageURL = strings.TrimSpace(matchedCard.ThumbnailURL)
		imageSource = "html_thumbnail"
	default:
		imageURL = ""
		imageSource = ""
	}

	item := model.EnrichedNewsItem{
		ID:            itemID,
		DisplayDate:   raw.DisplayDate,
		CategoryID:    raw.CategoryID,
		CategoryLabel: raw.CategoryLabel,

		Title:         raw.Title,
		Publisher:     publisher,
		GoogleNewsURL: raw.GoogleNewsURL,
		OriginURL:     originURL,
		CanonicalURL:  canonicalURL,
		ImageURL:      imageURL,

		PublishedAt: publishedAt,
		CollectedAt: raw.CollectedAt,
		FirstSeenAt: now,
		LastSeenAt:  now,

		Source:  raw.Source,
		Query:   raw.Query,
		RawGUID: raw.RawGUID,

		BestRank:   raw.Rank,
		LatestRank: raw.Rank,
		SeenCount:  1,

		LinkSource:  linkSource,
		ImageSource: imageSource,
	}

	return item, nil
}

func choosePublisher(rawPublisher string, matchedCard *model.HTMLNewsCard) string {
	rawPublisher = strings.TrimSpace(rawPublisher)
	if rawPublisher != "" {
		return rawPublisher
	}
	if matchedCard != nil && strings.TrimSpace(matchedCard.Publisher) != "" {
		return strings.TrimSpace(matchedCard.Publisher)
	}
	return ""
}

func hostnameOr(fallback string) string {
	name, err := os.Hostname()
	if err != nil || name == "" {
		return fallback
	}
	return name
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if strings.TrimSpace(v) != "" {
			return strings.TrimSpace(v)
		}
	}
	return ""
}

package redisstore

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/redis/go-redis/v9"
)

func StreamHTMLAugmented(prefix string) string {
	return fmt.Sprintf("%s:html_augmented", prefix)
}

func ParseHTMLCard(msg redis.XMessage) (model.HTMLNewsCard, error) {
	get := func(key string) string {
		if v, ok := msg.Values[key]; ok {
			return strings.TrimSpace(fmt.Sprint(v))
		}
		return ""
	}

	cardRank := 0
	if raw := get("card_rank"); raw != "" {
		v, err := strconv.Atoi(raw)
		if err != nil {
			return model.HTMLNewsCard{}, fmt.Errorf("invalid card_rank: %w", err)
		}
		cardRank = v
	}

	card := model.HTMLNewsCard{
		DisplayDate:   get("display_date"),
		CategoryID:    get("category_id"),
		CategoryLabel: get("category_label"),
		CardRank:      cardRank,
		Title:         get("title"),
		Publisher:     get("publisher"),
		GoogleNewsURL: get("google_news_url"),
		PossibleURL:   get("possible_url"),
		ThumbnailURL:  get("thumbnail_url"),
		CollectedAt:   get("collected_at"),
		Query:         get("query"),
		Source:        get("source"),
	}

	if card.DisplayDate == "" || card.CategoryID == "" || card.Title == "" {
		return model.HTMLNewsCard{}, fmt.Errorf("missing required html card fields msg_id=%s", msg.ID)
	}

	return card, nil
}

func ReadRecentHTMLCards(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	displayDate string,
	categoryID string,
	query string,
	limit int64,
) ([]model.HTMLNewsCard, error) {
	if limit <= 0 {
		limit = 200
	}

	stream := StreamHTMLAugmented(prefix)

	msgs, err := client.XRevRangeN(ctx, stream, "+", "-", limit).Result()
	if err != nil {
		return nil, fmt.Errorf("xrevrange html augmented: %w", err)
	}

	out := make([]model.HTMLNewsCard, 0, len(msgs))
	for _, msg := range msgs {
		card, err := ParseHTMLCard(msg)
		if err != nil {
			continue
		}

		if displayDate != "" && card.DisplayDate != displayDate {
			continue
		}
		if categoryID != "" && card.CategoryID != categoryID {
			continue
		}
		if query != "" && strings.TrimSpace(card.Query) != strings.TrimSpace(query) {
			continue
		}

		out = append(out, card)
	}

	return out, nil
}

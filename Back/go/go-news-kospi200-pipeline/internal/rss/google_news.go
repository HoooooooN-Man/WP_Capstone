package rss

import (
	"context"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/model"
	"github.com/example/go-news-kospi200-pipeline/internal/util"
	"github.com/mmcdole/gofeed"
)

type GoogleNewsClient struct {
	parser *gofeed.Parser
}

func NewGoogleNewsClient() *GoogleNewsClient {
	return &GoogleNewsClient{parser: gofeed.NewParser()}
}

func BuildSearchURL(query string) string {
	v := url.Values{}
	v.Set("q", query)
	v.Set("hl", "ko")
	v.Set("gl", "KR")
	v.Set("ceid", "KR:ko")
	return "https://news.google.com/rss/search?" + v.Encode()
}

func (c *GoogleNewsClient) Fetch(ctx context.Context, query string) ([]model.RawNewsEvent, error) {
	feed, err := c.parser.ParseURLWithContext(BuildSearchURL(query), ctx)
	if err != nil {
		return nil, err
	}

	now := time.Now()
	items := make([]model.RawNewsEvent, 0, len(feed.Items))

	for _, it := range feed.Items {
		published := now
		if it.PublishedParsed != nil {
			published = *it.PublishedParsed
		}

		cleanTitle, source := splitGoogleNewsTitle(it.Title)

		newsIDSeed := strings.Join([]string{
			query,
			cleanTitle,
			source,
			published.UTC().Format(time.RFC3339),
		}, "|")

		items = append(items, model.RawNewsEvent{
			NewsID:      util.SHA256Hex(newsIDSeed),
			Provider:    "google_news",
			Query:       query,
			Title:       cleanTitle,
			SourceName:  source,
			GoogleURL:   it.Link,
			ArticleURL:  "",
			Snippet:     firstNonEmpty(it.Description, it.Content),
			PublishedAt: published,
			FetchedAt:   now,
		})
	}

	return items, nil
}

func firstNonEmpty(items ...string) string {
	for _, it := range items {
		if s := strings.TrimSpace(it); s != "" {
			return s
		}
	}
	return ""
}

func splitGoogleNewsTitle(s string) (title string, source string) {
	s = strings.TrimSpace(s)
	if s == "" {
		return "", ""
	}

	parts := strings.Split(s, " - ")
	if len(parts) < 2 {
		return s, ""
	}

	source = strings.TrimSpace(parts[len(parts)-1])
	title = strings.TrimSpace(strings.Join(parts[:len(parts)-1], " - "))

	if title == "" {
		return s, ""
	}

	return title, source
}

func (c *GoogleNewsClient) DebugURL(query string) string {
	return fmt.Sprintf("query=%s url=%s", query, BuildSearchURL(query))
}

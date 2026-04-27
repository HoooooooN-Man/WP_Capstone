package collector

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/mmcdole/gofeed"
)

type GoogleRSSClient struct {
	client    *http.Client
	userAgent string
}

func NewGoogleRSSClient(timeout time.Duration, userAgent string) *GoogleRSSClient {
	return &GoogleRSSClient{
		client: &http.Client{
			Timeout: timeout,
		},
		userAgent: userAgent,
	}
}

func BuildSearchFeedURL(query string) string {
	q := url.QueryEscape(strings.TrimSpace(query))
	return fmt.Sprintf("https://news.google.com/rss/search?q=%s&hl=ko&gl=KR&ceid=KR:ko", q)
}

func (c *GoogleRSSClient) FetchByJob(ctx context.Context, job model.CollectJob) ([]model.RawNewsItem, error) {
	feedURL := strings.TrimSpace(job.FeedURL)
	if feedURL == "" {
		if strings.TrimSpace(job.Query) == "" {
			return nil, fmt.Errorf("job has neither feed_url nor query: category=%s", job.CategoryID)
		}
		feedURL = BuildSearchFeedURL(job.Query)
	}

	parser := gofeed.NewParser()
	parser.Client = &http.Client{
		Timeout: c.client.Timeout,
		Transport: roundTripperWithUA{
			base:      http.DefaultTransport,
			userAgent: c.userAgent,
		},
	}

	feed, err := parser.ParseURLWithContext(feedURL, ctx)
	if err != nil {
		return nil, fmt.Errorf("parse google rss feed: %w", err)
	}

	topN := job.TopN
	if topN <= 0 {
		topN = 10
	}

	items := make([]model.RawNewsItem, 0, topN)
	collectedAt := time.Now().Format(time.RFC3339)

	for idx, entry := range feed.Items {
		if idx >= topN {
			break
		}

		publisher := ""
		title, publisher := SplitTitleAndPublisher(entry.Title, publisher)

		publishedAt := ""
		if entry.PublishedParsed != nil {
			publishedAt = entry.PublishedParsed.Format(time.RFC3339)
		}

		items = append(items, model.RawNewsItem{
			DisplayDate:   job.DisplayDate,
			CategoryID:    job.CategoryID,
			CategoryLabel: job.CategoryLabel,
			Rank:          idx + 1,
			Title:         title,
			Publisher:     publisher,
			GoogleNewsURL: strings.TrimSpace(entry.Link),
			PublishedAt:   publishedAt,
			CollectedAt:   collectedAt,
			Source:        job.Source,
			Query:         job.Query,
			RawGUID:       strings.TrimSpace(entry.GUID),
		})
	}

	return items, nil
}

type roundTripperWithUA struct {
	base      http.RoundTripper
	userAgent string
}

func (rt roundTripperWithUA) RoundTrip(req *http.Request) (*http.Response, error) {
	clone := req.Clone(req.Context())
	if strings.TrimSpace(rt.userAgent) != "" {
		clone.Header.Set("User-Agent", rt.userAgent)
	}

	base := rt.base
	if base == nil {
		base = http.DefaultTransport
	}

	return base.RoundTrip(clone)
}

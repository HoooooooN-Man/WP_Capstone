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

	windowStart, windowEnd, hasWindow, err := parseJobWindow(job)
	if err != nil {
		return nil, err
	}

	items := make([]model.RawNewsItem, 0, topN)
	collectedAt := time.Now().Format(time.RFC3339)
	rank := 0

	for _, entry := range feed.Items {
		if len(items) >= topN {
			break
		}

		if hasWindow && !isPublishedInWindow(entry, windowStart, windowEnd) {
			continue
		}

		publisher := ""
		title, publisher := SplitTitleAndPublisher(entry.Title, publisher)

		publishedAt := ""
		if entry.PublishedParsed != nil {
			publishedAt = entry.PublishedParsed.Format(time.RFC3339)
		}

		rank++

		items = append(items, model.RawNewsItem{
			DisplayDate:   job.DisplayDate,
			CategoryID:    job.CategoryID,
			CategoryLabel: job.CategoryLabel,
			Rank:          rank,
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

func parseJobWindow(job model.CollectJob) (time.Time, time.Time, bool, error) {
	windowStartRaw := strings.TrimSpace(job.WindowStart)
	windowEndRaw := strings.TrimSpace(job.WindowEnd)

	if windowStartRaw == "" && windowEndRaw == "" {
		return time.Time{}, time.Time{}, false, nil
	}

	if windowStartRaw == "" || windowEndRaw == "" {
		return time.Time{}, time.Time{}, false, fmt.Errorf(
			"job has incomplete window: category=%s window_start=%q window_end=%q",
			job.CategoryID,
			job.WindowStart,
			job.WindowEnd,
		)
	}

	windowStart, err := time.Parse(time.RFC3339, windowStartRaw)
	if err != nil {
		return time.Time{}, time.Time{}, false, fmt.Errorf("parse window_start: %w", err)
	}

	windowEnd, err := time.Parse(time.RFC3339, windowEndRaw)
	if err != nil {
		return time.Time{}, time.Time{}, false, fmt.Errorf("parse window_end: %w", err)
	}

	if windowEnd.Before(windowStart) {
		return time.Time{}, time.Time{}, false, fmt.Errorf(
			"invalid job window: category=%s window_start=%s window_end=%s",
			job.CategoryID,
			job.WindowStart,
			job.WindowEnd,
		)
	}

	return windowStart, windowEnd, true, nil
}

func isPublishedInWindow(entry *gofeed.Item, windowStart, windowEnd time.Time) bool {
	if entry == nil || entry.PublishedParsed == nil {
		return false
	}

	published := *entry.PublishedParsed
	return !published.Before(windowStart) && !published.After(windowEnd)
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

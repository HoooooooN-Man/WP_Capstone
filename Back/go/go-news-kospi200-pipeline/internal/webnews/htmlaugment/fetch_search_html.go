package htmlaugment

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type Fetcher struct {
	client    *http.Client
	userAgent string
}

func NewFetcher(timeout time.Duration, userAgent string) *Fetcher {
	return &Fetcher{
		client: &http.Client{
			Timeout: timeout,
		},
		userAgent: userAgent,
	}
}

func BuildSearchHTMLURL(query string) string {
	q := url.QueryEscape(strings.TrimSpace(query))
	return fmt.Sprintf("https://news.google.com/search?q=%s&hl=ko&gl=KR&ceid=KR:ko", q)
}

func (f *Fetcher) FetchSearchHTML(ctx context.Context, query string) (string, string, error) {
	searchURL := BuildSearchHTMLURL(query)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, searchURL, nil)
	if err != nil {
		return "", "", fmt.Errorf("build request: %w", err)
	}
	if strings.TrimSpace(f.userAgent) != "" {
		req.Header.Set("User-Agent", f.userAgent)
	}
	req.Header.Set("Accept-Language", "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7")

	resp, err := f.client.Do(req)
	if err != nil {
		return "", "", fmt.Errorf("request search html: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 2*1024*1024))
	if err != nil {
		return "", "", fmt.Errorf("read search html: %w", err)
	}

	finalURL := searchURL
	if resp.Request != nil && resp.Request.URL != nil {
		finalURL = resp.Request.URL.String()
	}

	return string(body), finalURL, nil
}

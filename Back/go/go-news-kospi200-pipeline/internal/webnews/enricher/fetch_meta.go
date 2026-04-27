package enricher

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
)

type PageMeta struct {
	CanonicalURL string
	ImageURL     string
	PublishedAt  string
}

type MetaFetcher struct {
	client    *http.Client
	userAgent string
}

func NewMetaFetcher(timeout time.Duration, userAgent string) *MetaFetcher {
	return &MetaFetcher{
		client: &http.Client{
			Timeout: timeout,
		},
		userAgent: userAgent,
	}
}

func (f *MetaFetcher) FetchMeta(ctx context.Context, pageURL string) (PageMeta, error) {
	pageURL = strings.TrimSpace(pageURL)
	if pageURL == "" {
		return PageMeta{}, fmt.Errorf("empty page url")
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, pageURL, nil)
	if err != nil {
		return PageMeta{}, fmt.Errorf("build request: %w", err)
	}
	if strings.TrimSpace(f.userAgent) != "" {
		req.Header.Set("User-Agent", f.userAgent)
	}

	resp, err := f.client.Do(req)
	if err != nil {
		return PageMeta{}, fmt.Errorf("request page: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1024*1024))
	if err != nil {
		return PageMeta{}, fmt.Errorf("read page: %w", err)
	}

	html := string(body)
	finalURL := pageURL
	if resp.Request != nil && resp.Request.URL != nil {
		finalURL = resp.Request.URL.String()
	}

	meta := PageMeta{
		CanonicalURL: firstResolvedURL(finalURL,
			findMetaContent(html, `(?is)<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']`),
			findMetaContent(html, `(?is)<meta[^>]+property=["']og:url["'][^>]+content=["']([^"']+)["']`),
			firstJSONLDURL(html),
		),
		ImageURL: firstResolvedURL(finalURL,
			findMetaContent(html, `(?is)<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']`),
			findMetaContent(html, `(?is)<meta[^>]+property=["']og:image:url["'][^>]+content=["']([^"']+)["']`),
			findMetaContent(html, `(?is)<meta[^>]+property=["']og:image:secure_url["'][^>]+content=["']([^"']+)["']`),
			findMetaContent(html, `(?is)<meta[^>]+name=["']twitter:image["'][^>]+content=["']([^"']+)["']`),
			firstJSONLDImage(html),
		),
		PublishedAt: firstNonEmpty(
			findMetaContent(html, `(?is)<meta[^>]+property=["']article:published_time["'][^>]+content=["']([^"']+)["']`),
			findMetaContent(html, `(?is)<meta[^>]+name=["']pubdate["'][^>]+content=["']([^"']+)["']`),
			findMetaContent(html, `(?is)<meta[^>]+name=["']publish-date["'][^>]+content=["']([^"']+)["']`),
			findMetaContent(html, `(?is)<meta[^>]+name=["']date["'][^>]+content=["']([^"']+)["']`),
			findMetaContent(html, `(?is)<meta[^>]+property=["']og:pubdate["'][^>]+content=["']([^"']+)["']`),
			firstJSONLDDate(html),
		),
	}

	meta.CanonicalURL = normalizeHTTPURL(meta.CanonicalURL)

	// Google News 페이지에서만 얻은 대표 이미지는 품질이 낮은 경우가 많아서 비움
	if IsGoogleNewsLikeURL(finalURL) && isGoogleHostedImage(meta.ImageURL) {
		meta.ImageURL = ""
	}

	return meta, nil
}

func findMetaContent(html, pattern string) string {
	re := regexp.MustCompile(pattern)
	m := re.FindStringSubmatch(html)
	if len(m) >= 2 {
		return strings.TrimSpace(m[1])
	}
	return ""
}

func firstResolvedURL(base string, candidates ...string) string {
	for _, c := range candidates {
		c = strings.TrimSpace(c)
		if c == "" {
			continue
		}
		if resolved := resolveMaybeRelativeURL(base, c); resolved != "" {
			return normalizeHTTPURL(resolved)
		}
	}
	return ""
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if strings.TrimSpace(v) != "" {
			return strings.TrimSpace(v)
		}
	}
	return ""
}

func isGoogleHostedImage(raw string) bool {
	u, err := url.Parse(strings.TrimSpace(raw))
	if err != nil {
		return false
	}
	host := strings.ToLower(u.Host)
	return strings.Contains(host, "googleusercontent.com") ||
		strings.Contains(host, "gstatic.com") ||
		strings.Contains(host, "google.com")
}

var jsonLDBlockRE = regexp.MustCompile(`(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>`)

func firstJSONLDURL(html string) string {
	type result struct {
		URL string
	}
	r := result{}
	walkJSONLDBlocks(html, func(v any) {
		if r.URL != "" {
			return
		}
		if m, ok := v.(map[string]any); ok {
			for _, key := range []string{"url", "mainEntityOfPage"} {
				if s := extractJSONStringLike(m[key]); s != "" && strings.HasPrefix(strings.ToLower(s), "http") {
					r.URL = s
					return
				}
			}
		}
	})
	return r.URL
}

func firstJSONLDImage(html string) string {
	type result struct {
		URL string
	}
	r := result{}
	walkJSONLDBlocks(html, func(v any) {
		if r.URL != "" {
			return
		}
		if m, ok := v.(map[string]any); ok {
			if s := extractJSONStringLike(m["image"]); s != "" && strings.HasPrefix(strings.ToLower(s), "http") {
				r.URL = s
				return
			}
		}
	})
	return r.URL
}

func firstJSONLDDate(html string) string {
	type result struct {
		Date string
	}
	r := result{}
	walkJSONLDBlocks(html, func(v any) {
		if r.Date != "" {
			return
		}
		if m, ok := v.(map[string]any); ok {
			for _, key := range []string{"datePublished", "dateCreated", "uploadDate"} {
				if s := extractJSONStringLike(m[key]); s != "" {
					r.Date = s
					return
				}
			}
		}
	})
	return r.Date
}

func walkJSONLDBlocks(html string, fn func(any)) {
	matches := jsonLDBlockRE.FindAllStringSubmatch(html, 20)
	for _, m := range matches {
		if len(m) < 2 {
			continue
		}

		var data any
		if err := json.Unmarshal([]byte(strings.TrimSpace(m[1])), &data); err != nil {
			continue
		}

		walkAny(data, fn)
	}
}

func walkAny(v any, fn func(any)) {
	fn(v)

	switch t := v.(type) {
	case map[string]any:
		for _, vv := range t {
			walkAny(vv, fn)
		}
	case []any:
		for _, vv := range t {
			walkAny(vv, fn)
		}
	}
}

func extractJSONStringLike(v any) string {
	switch t := v.(type) {
	case string:
		return strings.TrimSpace(t)
	case []any:
		for _, vv := range t {
			if s, ok := vv.(string); ok && strings.TrimSpace(s) != "" {
				return strings.TrimSpace(s)
			}
		}
	case map[string]any:
		for _, key := range []string{"url", "@id"} {
			if s, ok := t[key].(string); ok && strings.TrimSpace(s) != "" {
				return strings.TrimSpace(s)
			}
		}
	}
	return ""
}

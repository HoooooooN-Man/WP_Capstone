package enricher

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"sort"
	"strings"
	"time"
)

type OriginResolver struct {
	client    *http.Client
	userAgent string
}

func NewOriginResolver(timeout time.Duration, userAgent string) *OriginResolver {
	return &OriginResolver{
		client: &http.Client{
			Timeout: timeout,
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				if len(via) >= 10 {
					return http.ErrUseLastResponse
				}
				return nil
			},
		},
		userAgent: userAgent,
	}
}

func (r *OriginResolver) ResolveOriginURL(ctx context.Context, googleNewsURL string) (string, error) {
	googleNewsURL = strings.TrimSpace(googleNewsURL)
	if googleNewsURL == "" {
		return "", fmt.Errorf("empty google news url")
	}

	// 1) URL 자체 query param에 원문 링크가 숨어 있으면 우선 사용
	if direct := extractDirectURLFromGoogleLikeURL(googleNewsURL); direct != "" && !IsBlockedOriginCandidateURL(direct) {
		return normalizeHTTPURL(direct), nil
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, googleNewsURL, nil)
	if err != nil {
		return "", fmt.Errorf("build request: %w", err)
	}
	if strings.TrimSpace(r.userAgent) != "" {
		req.Header.Set("User-Agent", r.userAgent)
	}

	resp, err := r.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request google news url: %w", err)
	}
	defer resp.Body.Close()

	finalURL := ""
	if resp.Request != nil && resp.Request.URL != nil {
		finalURL = strings.TrimSpace(resp.Request.URL.String())
	}

	bodyBytes, _ := io.ReadAll(io.LimitReader(resp.Body, 1024*1024))
	body := string(bodyBytes)

	// 2) redirect 결과가 이미 실제 원문이면 반환
	if finalURL != "" && !IsBlockedOriginCandidateURL(finalURL) {
		return normalizeHTTPURL(finalURL), nil
	}

	// 3) 최종 URL query param 안에 원문이 숨어 있으면 사용
	if direct := extractDirectURLFromGoogleLikeURL(finalURL); direct != "" && !IsBlockedOriginCandidateURL(direct) {
		return normalizeHTTPURL(direct), nil
	}

	// 4) HTML / JSON-LD / meta refresh / embedded URLs 에서 후보 추출
	candidates := extractCandidateURLs(body, finalURL)
	best := chooseBestArticleURL(candidates)
	if best != "" {
		return normalizeHTTPURL(best), nil
	}

	// 5) 끝까지 못 풀면 여기서는 google fallback을 반환하지 않고 빈 값
	//    -> caller에서 명시적으로 raw Google URL fallback 결정
	return "", nil
}

func IsGoogleNewsLikeURL(raw string) bool {
	u, err := url.Parse(strings.TrimSpace(raw))
	if err != nil {
		return false
	}
	host := strings.ToLower(u.Host)
	return strings.Contains(host, "news.google.com") ||
		strings.Contains(host, "google.com") ||
		strings.Contains(host, "googleusercontent.com") ||
		strings.Contains(host, "gstatic.com")
}

func IsBlockedOriginCandidateURL(raw string) bool {
	u, err := url.Parse(strings.TrimSpace(raw))
	if err != nil {
		return false
	}

	host := strings.ToLower(strings.TrimSpace(u.Host))
	if host == "" {
		return false
	}

	// Google / gstatic / googleusercontent 는 정식 origin/canonical 후보에서 제외
	if strings.Contains(host, "news.google.com") ||
		strings.Contains(host, "google.com") ||
		strings.Contains(host, "googleusercontent.com") ||
		strings.Contains(host, "gstatic.com") {
		return true
	}

	return false
}

func ChoosePreferredCanonicalURL(candidates ...string) string {
	for _, c := range candidates {
		c = normalizeHTTPURL(c)
		if c == "" {
			continue
		}
		if IsBlockedOriginCandidateURL(c) {
			continue
		}
		return c
	}
	return ""
}

func BuildItemID(canonicalURL, title, publisher string) string {
	key := strings.TrimSpace(canonicalURL)
	if key == "" || IsBlockedOriginCandidateURL(key) {
		key = normalizeForID(title) + "|" + normalizeForID(publisher)
	}

	sum := sha1.Sum([]byte(key))
	return hex.EncodeToString(sum[:])
}

var multiSpaceRE = regexp.MustCompile(`\s+`)

func normalizeForID(s string) string {
	s = strings.TrimSpace(strings.ToLower(s))
	s = strings.NewReplacer(
		"ㆍ", " ",
		"·", " ",
		"•", " ",
		"\t", " ",
		"\n", " ",
		"\r", " ",
	).Replace(s)

	s = multiSpaceRE.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

var canonicalLinkRE = regexp.MustCompile(`(?is)<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']`)
var ogURLRE = regexp.MustCompile(`(?is)<meta[^>]+property=["']og:url["'][^>]+content=["']([^"']+)["']`)
var metaRefreshRE = regexp.MustCompile(`(?is)<meta[^>]+http-equiv=["']refresh["'][^>]+content=["'][^"']*url=([^"']+)["']`)
var quotedURLInBodyRE = regexp.MustCompile(`https?://[^\s"'<>\\]+`)
var jsonLDRE = regexp.MustCompile(`(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>`)

func extractDirectURLFromGoogleLikeURL(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}

	u, err := url.Parse(raw)
	if err != nil {
		return ""
	}

	for _, key := range []string{"url", "u", "q", "continue", "redirect", "dest", "target"} {
		if v := strings.TrimSpace(u.Query().Get(key)); v != "" {
			if decoded := maybeDecodeNestedURL(v); decoded != "" {
				return decoded
			}
		}
	}

	return ""
}

func maybeDecodeNestedURL(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}

	for i := 0; i < 3; i++ {
		decoded, err := url.QueryUnescape(raw)
		if err != nil {
			break
		}
		if decoded == raw {
			break
		}
		raw = decoded
	}

	raw = strings.Trim(raw, `"'`)
	if strings.HasPrefix(raw, "http://") || strings.HasPrefix(raw, "https://") {
		return raw
	}
	return ""
}

func extractCandidateURLs(htmlText, base string) []string {
	candidates := make([]string, 0, 32)

	add := func(raw string) {
		raw = strings.TrimSpace(raw)
		if raw == "" {
			return
		}
		resolved := resolveMaybeRelativeURL(base, raw)
		if strings.TrimSpace(resolved) == "" {
			return
		}
		candidates = append(candidates, resolved)
	}

	if m := canonicalLinkRE.FindStringSubmatch(htmlText); len(m) >= 2 {
		add(m[1])
	}
	if m := ogURLRE.FindStringSubmatch(htmlText); len(m) >= 2 {
		add(m[1])
	}
	if m := metaRefreshRE.FindStringSubmatch(htmlText); len(m) >= 2 {
		add(m[1])
	}

	for _, u := range extractURLsFromJSONLD(htmlText) {
		add(u)
	}

	for _, key := range []string{"url", "u", "q", "continue", "redirect", "dest", "target"} {
		re := regexp.MustCompile(`(?i)["']` + key + `["']\s*:\s*["']([^"']+)["']`)
		for _, m := range re.FindAllStringSubmatch(htmlText, 20) {
			if len(m) >= 2 {
				add(m[1])
			}
		}
	}

	for _, raw := range quotedURLInBodyRE.FindAllString(htmlText, 50) {
		add(raw)
	}

	return dedupeStrings(candidates)
}

func extractURLsFromJSONLD(htmlText string) []string {
	var out []string

	matches := jsonLDRE.FindAllStringSubmatch(htmlText, 20)
	for _, m := range matches {
		if len(m) < 2 {
			continue
		}

		block := strings.TrimSpace(m[1])
		if block == "" {
			continue
		}

		var anyValue any
		if err := json.Unmarshal([]byte(block), &anyValue); err != nil {
			continue
		}

		collectURLsFromAny(anyValue, &out)
	}

	return dedupeStrings(out)
}

func collectURLsFromAny(v any, out *[]string) {
	switch t := v.(type) {
	case map[string]any:
		for k, vv := range t {
			lk := strings.ToLower(strings.TrimSpace(k))
			if (lk == "url" || lk == "mainentityofpage" || lk == "sameas") && isStringOrStringArray(vv) {
				collectStringLike(vv, out)
			}
			collectURLsFromAny(vv, out)
		}
	case []any:
		for _, vv := range t {
			collectURLsFromAny(vv, out)
		}
	}
}

func isStringOrStringArray(v any) bool {
	switch v.(type) {
	case string:
		return true
	case []any:
		return true
	default:
		return false
	}
}

func collectStringLike(v any, out *[]string) {
	switch t := v.(type) {
	case string:
		if strings.HasPrefix(strings.TrimSpace(t), "http://") || strings.HasPrefix(strings.TrimSpace(t), "https://") {
			*out = append(*out, t)
		}
	case []any:
		for _, vv := range t {
			if s, ok := vv.(string); ok {
				if strings.HasPrefix(strings.TrimSpace(s), "http://") || strings.HasPrefix(strings.TrimSpace(s), "https://") {
					*out = append(*out, s)
				}
			}
		}
	}
}

func chooseBestArticleURL(candidates []string) string {
	type scored struct {
		URL   string
		Score int
	}

	scoredList := make([]scored, 0, len(candidates))
	for _, c := range candidates {
		c = normalizeHTTPURL(c)
		if c == "" {
			continue
		}
		if IsBlockedOriginCandidateURL(c) {
			continue
		}

		score := 0
		lc := strings.ToLower(c)

		if strings.HasPrefix(lc, "https://") {
			score += 5
		}
		if strings.Contains(lc, "/article") || strings.Contains(lc, "/news") || strings.Contains(lc, "/articles/") || strings.Contains(lc, "/view") {
			score += 10
		}
		if strings.Contains(lc, "amp") {
			score -= 3
		}
		if len(lc) > 30 {
			score += 2
		}

		scoredList = append(scoredList, scored{URL: c, Score: score})
	}

	if len(scoredList) == 0 {
		return ""
	}

	sort.SliceStable(scoredList, func(i, j int) bool {
		if scoredList[i].Score == scoredList[j].Score {
			return len(scoredList[i].URL) > len(scoredList[j].URL)
		}
		return scoredList[i].Score > scoredList[j].Score
	})

	return scoredList[0].URL
}

func resolveMaybeRelativeURL(base, raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}

	if nested := maybeDecodeNestedURL(raw); nested != "" {
		raw = nested
	}

	u, err := url.Parse(raw)
	if err == nil && u.IsAbs() {
		return u.String()
	}

	if strings.TrimSpace(base) == "" {
		return raw
	}

	bu, err := url.Parse(base)
	if err != nil {
		return raw
	}
	ru, err := url.Parse(raw)
	if err != nil {
		return raw
	}

	return bu.ResolveReference(ru).String()
}

func normalizeHTTPURL(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}

	u, err := url.Parse(raw)
	if err != nil {
		return raw
	}

	u.Fragment = ""

	// Google RSS 파라미터 일부 정리
	q := u.Query()
	if strings.Contains(strings.ToLower(u.Host), "news.google.com") {
		for _, key := range []string{"hl", "gl", "ceid"} {
			q.Del(key)
		}
		u.RawQuery = q.Encode()
	}

	return u.String()
}

func dedupeStrings(values []string) []string {
	seen := map[string]struct{}{}
	out := make([]string, 0, len(values))

	for _, v := range values {
		v = strings.TrimSpace(v)
		if v == "" {
			continue
		}
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = struct{}{}
		out = append(out, v)
	}

	return out
}

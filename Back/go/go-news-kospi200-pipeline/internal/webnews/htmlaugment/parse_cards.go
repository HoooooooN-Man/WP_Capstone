package htmlaugment

import (
	"net/url"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/collector"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"golang.org/x/net/html"
)

func ParseCardsFromSearchHTML(
	htmlText string,
	finalURL string,
	displayDate string,
	categoryID string,
	categoryLabel string,
	query string,
	topN int,
) ([]model.HTMLNewsCard, error) {
	doc, err := html.Parse(strings.NewReader(htmlText))
	if err != nil {
		return nil, err
	}

	if topN <= 0 {
		topN = 10
	}

	baseURL := finalURL
	if strings.TrimSpace(baseURL) == "" {
		baseURL = "https://news.google.com/"
	}

	anchors := findArticleAnchors(doc)
	cards := make([]model.HTMLNewsCard, 0, topN)
	seen := map[string]struct{}{}

	collectedAt := nowRFC3339()

	for _, a := range anchors {
		if len(cards) >= topN {
			break
		}

		title := collector.NormalizeTitle(textContent(a))
		if title == "" || len([]rune(title)) < 8 {
			continue
		}

		href := attr(a, "href")
		googleURL := resolveNewsURL(baseURL, href)
		if strings.TrimSpace(googleURL) == "" {
			continue
		}

		key := strings.ToLower(strings.TrimSpace(title)) + "|" + googleURL
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}

		container := nearestContainer(a)

		publisher := extractPublisher(container, title)
		thumbnail := extractThumbnail(container, baseURL)
		possibleURL := extractPossibleURL(container, baseURL, googleURL)

		cards = append(cards, model.HTMLNewsCard{
			DisplayDate:   displayDate,
			CategoryID:    categoryID,
			CategoryLabel: categoryLabel,
			CardRank:      len(cards) + 1,
			Title:         title,
			Publisher:     publisher,
			GoogleNewsURL: googleURL,
			PossibleURL:   possibleURL,
			ThumbnailURL:  thumbnail,
			CollectedAt:   collectedAt,
			Query:         query,
			Source:        "google_news_html",
		})
	}

	return cards, nil
}

func findArticleAnchors(root *html.Node) []*html.Node {
	var out []*html.Node

	var walk func(*html.Node)
	walk = func(n *html.Node) {
		if n == nil {
			return
		}

		if n.Type == html.ElementNode && n.Data == "a" {
			href := strings.TrimSpace(attr(n, "href"))
			title := collector.NormalizeTitle(textContent(n))

			if isGoogleArticleHref(href) && title != "" {
				out = append(out, n)
			}
		}

		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(root)
	return out
}

func isGoogleArticleHref(href string) bool {
	href = strings.TrimSpace(href)
	if href == "" {
		return false
	}

	return strings.HasPrefix(href, "./articles/") ||
		strings.HasPrefix(href, "/articles/") ||
		strings.HasPrefix(href, "./read/") ||
		strings.HasPrefix(href, "/read/")
}

func nearestContainer(n *html.Node) *html.Node {
	cur := n
	for i := 0; cur != nil && i < 8; i++ {
		if cur.Type == html.ElementNode {
			if cur.Data == "article" || cur.Data == "c-wiz" || cur.Data == "div" {
				return cur
			}
		}
		cur = cur.Parent
	}
	if n != nil && n.Parent != nil {
		return n.Parent
	}
	return n
}

func extractPublisher(container *html.Node, title string) string {
	if container == nil {
		return ""
	}

	candidates := make([]string, 0, 12)

	var walk func(*html.Node)
	walk = func(n *html.Node) {
		if n == nil {
			return
		}

		if n.Type == html.ElementNode && (n.Data == "a" || n.Data == "span" || n.Data == "div") {
			txt := collector.CleanPublisher(textContent(n))
			if txt != "" &&
				txt != title &&
				len([]rune(txt)) <= 40 &&
				!strings.Contains(txt, "시간 전") &&
				!strings.Contains(txt, "분 전") &&
				!strings.Contains(strings.ToLower(txt), "favicon") {
				candidates = append(candidates, txt)
			}
		}

		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(container)

	seen := map[string]struct{}{}
	for _, c := range candidates {
		if _, ok := seen[c]; ok {
			continue
		}
		seen[c] = struct{}{}
		if looksLikePublisher(c) {
			return c
		}
	}

	return ""
}

func looksLikePublisher(s string) bool {
	s = strings.TrimSpace(s)
	if s == "" {
		return false
	}
	if len([]rune(s)) > 40 {
		return false
	}
	lc := strings.ToLower(s)
	if strings.Contains(s, "더보기") ||
		strings.Contains(s, "관련") ||
		strings.Contains(lc, "google") ||
		strings.Contains(lc, "news") {
		return false
	}
	return true
}

type scoredCandidate struct {
	Value string
	Score int
}

func extractThumbnail(container *html.Node, baseURL string) string {
	if container == nil {
		return ""
	}

	candidates := make([]scoredCandidate, 0, 16)

	var walk func(*html.Node)
	walk = func(n *html.Node) {
		if n == nil {
			return
		}

		if n.Type == html.ElementNode && n.Data == "img" {
			for _, key := range []string{
				"src", "data-src", "data-iurl", "data-image-url",
				"srcset", "data-srcset", "data-lzy_src",
			} {
				raw := strings.TrimSpace(attr(n, key))
				if raw == "" {
					continue
				}
				if key == "srcset" || key == "data-srcset" {
					raw = firstSrcsetURL(raw)
				}
				resolved := resolveNewsURL(baseURL, raw)
				if resolved == "" {
					continue
				}
				score := scoreImageURL(resolved)
				if score <= 0 {
					continue
				}
				candidates = append(candidates, scoredCandidate{
					Value: resolved,
					Score: score,
				})
			}
		}

		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(container)

	if len(candidates) == 0 {
		return ""
	}

	sort.SliceStable(candidates, func(i, j int) bool {
		if candidates[i].Score == candidates[j].Score {
			return len(candidates[i].Value) > len(candidates[j].Value)
		}
		return candidates[i].Score > candidates[j].Score
	})

	return candidates[0].Value
}

func scoreImageURL(raw string) int {
	lc := strings.ToLower(strings.TrimSpace(raw))
	if lc == "" {
		return 0
	}

	// favicon 류는 버린다
	if isFaviconLikeURL(lc) {
		return 0
	}

	score := 0

	if strings.HasPrefix(lc, "https://") {
		score += 5
	}
	if strings.Contains(lc, "gstatic.com") || strings.Contains(lc, "googleusercontent.com") {
		score += 3
	}
	if strings.Contains(lc, "encrypted-tbn") {
		score += 8
	}
	if strings.Contains(lc, "image") || strings.Contains(lc, "img") || strings.Contains(lc, "thumbnail") {
		score += 4
	}
	if strings.Contains(lc, ".jpg") || strings.Contains(lc, ".jpeg") || strings.Contains(lc, ".png") || strings.Contains(lc, ".webp") {
		score += 5
	}
	if strings.Contains(lc, "w300") || strings.Contains(lc, "w600") || strings.Contains(lc, "w800") {
		score += 2
	}

	return score
}

func isFaviconLikeURL(raw string) bool {
	lc := strings.ToLower(strings.TrimSpace(raw))
	if lc == "" {
		return false
	}

	return strings.Contains(lc, "faviconv2") ||
		strings.Contains(lc, "type=favicon") ||
		strings.Contains(lc, "/favicon") ||
		strings.Contains(lc, "fallback_opts=type,size,url")
}

func extractPossibleURL(container *html.Node, baseURL string, googleURL string) string {
	if container == nil {
		return ""
	}

	candidates := make([]scoredCandidate, 0, 32)

	addCandidate := func(raw string) {
		for _, c := range extractURLCandidates(raw, baseURL) {
			if c == "" || c == googleURL {
				continue
			}
			score := scorePossibleURL(c)
			if score <= 0 {
				continue
			}
			candidates = append(candidates, scoredCandidate{
				Value: c,
				Score: score,
			})
		}
	}

	var walk func(*html.Node)
	walk = func(n *html.Node) {
		if n == nil {
			return
		}

		if n.Type == html.ElementNode {
			for _, a := range n.Attr {
				if strings.TrimSpace(a.Val) == "" {
					continue
				}
				addCandidate(a.Val)
			}
		}

		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(container)

	if len(candidates) == 0 {
		return ""
	}

	sort.SliceStable(candidates, func(i, j int) bool {
		if candidates[i].Score == candidates[j].Score {
			return len(candidates[i].Value) > len(candidates[j].Value)
		}
		return candidates[i].Score > candidates[j].Score
	})

	return candidates[0].Value
}

func extractURLCandidates(raw string, baseURL string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}

	out := make([]string, 0, 8)

	add := func(v string) {
		v = strings.TrimSpace(v)
		if v == "" {
			return
		}
		resolved := resolveNewsURL(baseURL, v)
		if resolved != "" {
			out = append(out, resolved)
		}
	}

	// 1) 값 자체가 URL/상대경로인 경우
	if looksLikeURLOrPath(raw) {
		add(raw)
	}

	// 2) 문자열 안에 직접 포함된 URL
	for _, m := range httpURLRE.FindAllString(raw, 10) {
		add(m)
	}

	// 3) query param 안의 nested URL
	if u, err := url.Parse(raw); err == nil {
		q := u.Query()
		for _, key := range []string{"url", "u", "q", "continue", "redirect", "dest", "target", "imgurl", "adurl"} {
			if v := strings.TrimSpace(q.Get(key)); v != "" {
				add(v)
				if dec, err := url.QueryUnescape(v); err == nil {
					add(dec)
				}
			}
		}
	}

	// 4) raw 전체를 한 번 unescape
	if dec, err := url.QueryUnescape(raw); err == nil && dec != raw {
		if looksLikeURLOrPath(dec) {
			add(dec)
		}
		for _, m := range httpURLRE.FindAllString(dec, 10) {
			add(m)
		}
	}

	return dedupeValues(out)
}

var httpURLRE = regexp.MustCompile(`https?://[^\s"'<>\\]+`)

func looksLikeURLOrPath(raw string) bool {
	raw = strings.TrimSpace(raw)
	return strings.HasPrefix(raw, "http://") ||
		strings.HasPrefix(raw, "https://") ||
		strings.HasPrefix(raw, "//") ||
		strings.HasPrefix(raw, "/") ||
		strings.HasPrefix(raw, "./")
}

func scorePossibleURL(raw string) int {
	lc := strings.ToLower(strings.TrimSpace(raw))
	if lc == "" {
		return 0
	}

	if strings.Contains(lc, "news.google.com") || strings.Contains(lc, "google.com") {
		return 0
	}
	if strings.Contains(lc, "gstatic.com") || strings.Contains(lc, "googleusercontent.com") {
		return 0
	}
	if isFaviconLikeURL(lc) {
		return 0
	}

	score := 0
	if strings.HasPrefix(lc, "https://") {
		score += 5
	}
	if strings.Contains(lc, "/article") || strings.Contains(lc, "/news") || strings.Contains(lc, "/view") {
		score += 10
	}
	if strings.Contains(lc, ".kr/") || strings.Contains(lc, ".com/") || strings.Contains(lc, ".net/") {
		score += 3
	}
	if len(lc) > 30 {
		score += 2
	}

	return score
}

func firstSrcsetURL(srcset string) string {
	srcset = strings.TrimSpace(srcset)
	if srcset == "" {
		return ""
	}

	parts := strings.Split(srcset, ",")
	if len(parts) == 0 {
		return ""
	}

	first := strings.TrimSpace(parts[0])
	fields := strings.Fields(first)
	if len(fields) == 0 {
		return ""
	}

	return strings.TrimSpace(fields[0])
}

func resolveNewsURL(baseURL, raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}

	if strings.HasPrefix(raw, "//") {
		return "https:" + raw
	}

	u, err := url.Parse(raw)
	if err == nil && u.IsAbs() {
		return u.String()
	}

	base, err := url.Parse(baseURL)
	if err != nil {
		base, _ = url.Parse("https://news.google.com/")
	}

	rel, err := url.Parse(raw)
	if err != nil {
		return ""
	}

	return base.ResolveReference(rel).String()
}

func attr(n *html.Node, key string) string {
	for _, a := range n.Attr {
		if a.Key == key {
			return a.Val
		}
	}
	return ""
}

func textContent(n *html.Node) string {
	if n == nil {
		return ""
	}

	var b strings.Builder

	var walk func(*html.Node)
	walk = func(cur *html.Node) {
		if cur == nil {
			return
		}
		if cur.Type == html.TextNode {
			b.WriteString(cur.Data)
			b.WriteString(" ")
		}
		for c := cur.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(n)
	return strings.TrimSpace(b.String())
}

func dedupeValues(values []string) []string {
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

func nowRFC3339() string {
	return time.Now().Format(time.RFC3339)
}

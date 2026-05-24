package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	xhtml "golang.org/x/net/html"
	"golang.org/x/net/html/charset"
	"golang.org/x/text/transform"
)

var categories = []string{
	"korea",
	"world",
	"business",
	"science_tech",
	"policy_finance",
	"industry_ai",
}

type ResolveRecord struct {
	ItemID        string `json:"item_id"`
	DisplayDate   string `json:"display_date,omitempty"`
	Category      string `json:"category"`
	Rank          int    `json:"rank"`
	Title         string `json:"title"`
	Publisher     string `json:"publisher,omitempty"`
	PublishedAt   string `json:"published_at,omitempty"`
	GoogleNewsURL string `json:"google_news_url"`
	ResolvedURL   string `json:"resolved_url,omitempty"`
	ResolveStatus string `json:"resolve_status"`
	Error         string `json:"error,omitempty"`
	ResolvedAt    string `json:"resolved_at,omitempty"`
}

type BodyRecord struct {
	ItemID        string `json:"item_id"`
	DisplayDate   string `json:"display_date,omitempty"`
	Category      string `json:"category"`
	Rank          int    `json:"rank"`
	Title         string `json:"title"`
	Publisher     string `json:"publisher,omitempty"`
	PublishedAt   string `json:"published_at,omitempty"`
	GoogleNewsURL string `json:"google_news_url"`
	ResolvedURL   string `json:"resolved_url,omitempty"`
	FinalURL      string `json:"final_url,omitempty"`
	FetchStatus   string `json:"fetch_status"`
	Error         string `json:"error,omitempty"`
	BodyText      string `json:"body_text"`
	BodyCharCount int    `json:"body_char_count"`
	FetchedAt     string `json:"fetched_at"`
}

type CategoryResult struct {
	Category        string `json:"category"`
	InputPath       string `json:"input_path"`
	OutputPath      string `json:"output_path"`
	SourceItemCount int    `json:"source_item_count"`
	WrittenCount    int    `json:"written_count"`
	SuccessCount    int    `json:"success_count"`
	FailedCount     int    `json:"failed_count"`
}

type BodyFetchManifest struct {
	SchemaVersion string           `json:"schema_version"`
	DisplayDate   string           `json:"display_date,omitempty"`
	GeneratedAt   string           `json:"generated_at"`
	ResolvedDir   string           `json:"resolved_dir"`
	OutputDir     string           `json:"output_dir"`
	MaxItems      int              `json:"max_items_per_category"`
	MaxBodyChars  int              `json:"max_body_chars"`
	Results       []CategoryResult `json:"results"`
}

func main() {
	resolvedDir := flag.String("resolved-dir", "data/webnews/current/llm_resolved", "directory containing resolved jsonl files")
	outputDir := flag.String("output-dir", "data/webnews/current/llm_input", "directory to write category body jsonl files")
	maxItems := flag.Int("max-items-per-category", 10, "max items to fetch per category")
	maxBodyChars := flag.Int("max-body-chars", 2500, "max body chars per article")
	minBodyChars := flag.Int("min-body-chars", 200, "minimum chars required to mark body fetch as ok")
	timeoutSeconds := flag.Int("timeout-seconds", 10, "http timeout seconds")
	delayMs := flag.Int("delay-ms", 500, "delay between article requests in milliseconds")
	userAgent := flag.String("user-agent", "Mozilla/5.0 WP-Capstone-WebNewsBot/1.0", "http user-agent")
	flag.Parse()

	if err := os.MkdirAll(*outputDir, 0755); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] create output dir: %v\n", err)
		os.Exit(1)
	}

	displayDate := readDisplayDateFromResolvedManifest(*resolvedDir)

	client := &http.Client{
		Timeout: time.Duration(*timeoutSeconds) * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 8 {
				return http.ErrUseLastResponse
			}
			return nil
		},
	}

	manifest := BodyFetchManifest{
		SchemaVersion: "webnews-body-fetch.v1",
		DisplayDate:   displayDate,
		GeneratedAt:   time.Now().Format(time.RFC3339),
		ResolvedDir:   *resolvedDir,
		OutputDir:     *outputDir,
		MaxItems:      *maxItems,
		MaxBodyChars:  *maxBodyChars,
		Results:       make([]CategoryResult, 0, len(categories)),
	}

	for _, category := range categories {
		result := processCategory(
			client,
			*resolvedDir,
			*outputDir,
			category,
			*maxItems,
			*maxBodyChars,
			*minBodyChars,
			time.Duration(*delayMs)*time.Millisecond,
			*userAgent,
		)

		manifest.Results = append(manifest.Results, result)

		fmt.Printf(
			"[body_fetcher] category=%s source=%d written=%d ok=%d failed=%d output=%s\n",
			result.Category,
			result.SourceItemCount,
			result.WrittenCount,
			result.SuccessCount,
			result.FailedCount,
			result.OutputPath,
		)
	}

	if err := writeJSONAtomic(filepath.Join(*outputDir, "articles_body.manifest.json"), manifest); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] write manifest: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[body_fetcher] done")
}

func processCategory(
	client *http.Client,
	resolvedDir string,
	outputDir string,
	category string,
	maxItems int,
	maxBodyChars int,
	minBodyChars int,
	delay time.Duration,
	userAgent string,
) CategoryResult {
	inputPath := filepath.Join(resolvedDir, category+".resolved.jsonl")
	outputPath := filepath.Join(outputDir, category+".body.jsonl")
	tmpPath := outputPath + ".tmp"

	records, err := loadResolvedJSONL(inputPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[WARN] load resolved category=%s path=%s err=%v\n", category, inputPath, err)
		return CategoryResult{
			Category:   category,
			InputPath:  inputPath,
			OutputPath: outputPath,
		}
	}

	f, err := os.Create(tmpPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[WARN] create output category=%s err=%v\n", category, err)
		return CategoryResult{
			Category:        category,
			InputPath:       inputPath,
			OutputPath:      outputPath,
			SourceItemCount: len(records),
		}
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetEscapeHTML(false)

	result := CategoryResult{
		Category:        category,
		InputPath:       inputPath,
		OutputPath:      outputPath,
		SourceItemCount: len(records),
	}

	limit := len(records)
	if maxItems > 0 && limit > maxItems {
		limit = maxItems
	}

	for i := 0; i < limit; i++ {
		src := records[i]

		rec := BodyRecord{
			ItemID:        src.ItemID,
			DisplayDate:   src.DisplayDate,
			Category:      src.Category,
			Rank:          src.Rank,
			Title:         src.Title,
			Publisher:     src.Publisher,
			PublishedAt:   src.PublishedAt,
			GoogleNewsURL: src.GoogleNewsURL,
			ResolvedURL:   src.ResolvedURL,
			FetchStatus:   "failed",
			Error:         "",
			BodyText:      "",
			BodyCharCount: 0,
			FetchedAt:     time.Now().Format(time.RFC3339),
		}

		if src.ResolveStatus != "ok" || src.ResolvedURL == "" {
			if src.Error != "" {
				rec.Error = "resolve_failed:" + src.Error
			} else {
				rec.Error = "resolve_failed"
			}
			result.FailedCount++
		} else {
			body, finalURL, fetchErr := fetchArticleBody(client, src.ResolvedURL, userAgent, maxBodyChars, minBodyChars)
			rec.FinalURL = finalURL

			if fetchErr != nil {
				rec.Error = fetchErr.Error()
				result.FailedCount++
			} else {
				rec.FetchStatus = "ok"
				rec.BodyText = body
				rec.BodyCharCount = len([]rune(body))
				result.SuccessCount++
			}
		}

		if err := enc.Encode(rec); err != nil {
			fmt.Fprintf(os.Stderr, "[WARN] write record category=%s item_id=%s err=%v\n", category, src.ItemID, err)
		} else {
			result.WrittenCount++
		}

		if delay > 0 {
			time.Sleep(delay)
		}
	}

	if err := f.Close(); err != nil {
		fmt.Fprintf(os.Stderr, "[WARN] close output category=%s err=%v\n", category, err)
	}

	if err := os.Rename(tmpPath, outputPath); err != nil {
		fmt.Fprintf(os.Stderr, "[WARN] rename output category=%s err=%v\n", category, err)
	}

	return result
}

func loadResolvedJSONL(path string) ([]ResolveRecord, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	lines := strings.Split(string(data), "\n")
	out := make([]ResolveRecord, 0, len(lines))

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		var rec ResolveRecord
		if err := json.Unmarshal([]byte(line), &rec); err != nil {
			return nil, err
		}

		out = append(out, rec)
	}

	return out, nil
}

func fetchArticleBody(
	client *http.Client,
	rawURL string,
	userAgent string,
	maxBodyChars int,
	minBodyChars int,
) (string, string, error) {
	req, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return "", "", fmt.Errorf("request_create_failed")
	}

	setBrowserHeaders(req, userAgent)

	resp, err := client.Do(req)
	if err != nil {
		return "", "", fmt.Errorf("http_request_failed")
	}
	defer resp.Body.Close()

	finalURL := ""
	if resp.Request != nil && resp.Request.URL != nil {
		finalURL = resp.Request.URL.String()
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		return "", finalURL, fmt.Errorf("http_status_%d", resp.StatusCode)
	}

	raw, err := io.ReadAll(io.LimitReader(resp.Body, 5*1024*1024))
	if err != nil {
		return "", finalURL, fmt.Errorf("read_body_failed")
	}

	utf8HTML, err := decodeToUTF8(raw, resp.Header.Get("Content-Type"))
	if err != nil {
		return "", finalURL, fmt.Errorf("decode_failed")
	}

	body := extractReadableText(utf8HTML)
	body = clipRunes(body, maxBodyChars)

	if len([]rune(body)) < minBodyChars {
		return "", finalURL, fmt.Errorf("body_too_short")
	}

	return body, finalURL, nil
}

func setBrowserHeaders(req *http.Request, userAgent string) {
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6")
	req.Header.Set("Cache-Control", "no-cache")
}

func decodeToUTF8(raw []byte, contentType string) (string, error) {
	enc, _, _ := charset.DetermineEncoding(raw, contentType)

	reader := transform.NewReader(bytes.NewReader(raw), enc.NewDecoder())
	decoded, err := io.ReadAll(reader)
	if err != nil {
		return "", err
	}

	return string(decoded), nil
}

func extractReadableText(htmlText string) string {
	doc, err := xhtml.Parse(strings.NewReader(htmlText))
	if err != nil {
		return ""
	}

	// 1순위: article 태그
	articleTexts := collectTextsByTag(doc, "article")
	for _, text := range articleTexts {
		text = normalizeText(text)
		if len([]rune(text)) >= 200 {
			return text
		}
	}

	// 2순위: article/content/news/body/view 계열 class/id
	hintTexts := collectTextsByArticleHints(doc)
	for _, text := range hintTexts {
		text = normalizeText(text)
		if len([]rune(text)) >= 200 {
			return text
		}
	}

	// 3순위: meta description
	metaDescription := collectMetaDescription(doc)
	if len([]rune(metaDescription)) >= 200 {
		return normalizeText(metaDescription)
	}

	// 4순위: p 태그 전체
	paragraphs := collectParagraphTexts(doc)
	if len(paragraphs) > 0 {
		return normalizeText(strings.Join(paragraphs, "\n"))
	}

	return ""
}

func collectTextsByTag(n *xhtml.Node, tag string) []string {
	var out []string

	var walk func(*xhtml.Node)
	walk = func(cur *xhtml.Node) {
		if cur.Type == xhtml.ElementNode && strings.EqualFold(cur.Data, tag) {
			text := normalizeText(textContent(cur))
			if text != "" && !looksLikeBoilerplate(text) {
				out = append(out, text)
			}
			return
		}

		for c := cur.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(n)
	return out
}

func collectTextsByArticleHints(n *xhtml.Node) []string {
	var out []string
	seen := map[string]bool{}

	var walk func(*xhtml.Node)
	walk = func(cur *xhtml.Node) {
		if cur.Type == xhtml.ElementNode && shouldSkipElement(cur.Data) {
			return
		}

		if cur.Type == xhtml.ElementNode && hasArticleHint(cur) {
			text := normalizeText(textContent(cur))
			if len([]rune(text)) >= 200 && !seen[text] && !looksLikeBoilerplate(text) {
				seen[text] = true
				out = append(out, text)
			}
		}

		for c := cur.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(n)
	return out
}

func hasArticleHint(n *xhtml.Node) bool {
	for _, attr := range n.Attr {
		key := strings.ToLower(attr.Key)
		val := strings.ToLower(attr.Val)

		if key != "id" && key != "class" && key != "itemprop" {
			continue
		}

		hints := []string{
			"article",
			"articlebody",
			"article_body",
			"article-view",
			"article_view",
			"newsbody",
			"news_body",
			"news-content",
			"news_content",
			"content",
			"contents",
			"view",
			"story",
			"본문",
		}

		for _, hint := range hints {
			if strings.Contains(val, strings.ToLower(hint)) {
				return true
			}
		}
	}

	return false
}

func collectMetaDescription(n *xhtml.Node) string {
	var values []string

	var walk func(*xhtml.Node)
	walk = func(cur *xhtml.Node) {
		if cur.Type == xhtml.ElementNode && strings.EqualFold(cur.Data, "meta") {
			var name string
			var property string
			var content string

			for _, attr := range cur.Attr {
				switch strings.ToLower(attr.Key) {
				case "name":
					name = strings.ToLower(attr.Val)
				case "property":
					property = strings.ToLower(attr.Val)
				case "content":
					content = strings.TrimSpace(attr.Val)
				}
			}

			if content != "" && (name == "description" || property == "og:description" || property == "twitter:description") {
				values = append(values, content)
			}
		}

		for c := cur.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(n)

	return normalizeText(strings.Join(values, " "))
}

func collectParagraphTexts(n *xhtml.Node) []string {
	var paragraphs []string
	seen := map[string]bool{}

	var walk func(*xhtml.Node)
	walk = func(cur *xhtml.Node) {
		if cur.Type == xhtml.ElementNode && shouldSkipElement(cur.Data) {
			return
		}

		if cur.Type == xhtml.ElementNode && strings.EqualFold(cur.Data, "p") {
			text := normalizeText(textContent(cur))
			if len([]rune(text)) >= 30 && !seen[text] && !looksLikeBoilerplate(text) {
				seen[text] = true
				paragraphs = append(paragraphs, text)
			}
			return
		}

		for c := cur.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}

	walk(n)
	return paragraphs
}

func textContent(n *xhtml.Node) string {
	if n == nil {
		return ""
	}

	if n.Type == xhtml.ElementNode && shouldSkipElement(n.Data) {
		return ""
	}

	if n.Type == xhtml.TextNode {
		return n.Data
	}

	var parts []string
	for c := n.FirstChild; c != nil; c = c.NextSibling {
		text := textContent(c)
		if text != "" {
			parts = append(parts, text)
		}
	}

	return strings.Join(parts, " ")
}

func shouldSkipElement(tag string) bool {
	switch strings.ToLower(tag) {
	case "script", "style", "noscript", "svg", "form", "input", "button",
		"nav", "header", "footer", "aside", "iframe", "figure":
		return true
	default:
		return false
	}
}

func looksLikeBoilerplate(text string) bool {
	lower := strings.ToLower(text)

	blockList := []string{
		"무단전재",
		"재배포 금지",
		"저작권자",
		"copyright",
		"all rights reserved",
		"구독",
		"로그인",
		"회원가입",
		"관련기사",
		"당신을 위한",
		"많이 본 뉴스",
		"기사제보",
		"광고문의",
		"개인정보처리방침",
	}

	for _, word := range blockList {
		if strings.Contains(lower, strings.ToLower(word)) {
			return true
		}
	}

	return false
}

func normalizeText(s string) string {
	s = strings.ReplaceAll(s, "\u00a0", " ")
	s = strings.ReplaceAll(s, "\t", " ")
	s = strings.ReplaceAll(s, "\r", " ")
	s = strings.ReplaceAll(s, "\n", " ")

	fields := strings.Fields(s)
	return strings.TrimSpace(strings.Join(fields, " "))
}

func clipRunes(s string, max int) string {
	if max <= 0 {
		return s
	}

	runes := []rune(s)
	if len(runes) <= max {
		return s
	}

	return string(runes[:max])
}

func readDisplayDateFromResolvedManifest(resolvedDir string) string {
	path := filepath.Join(resolvedDir, "resolved.manifest.json")

	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}

	var m map[string]any
	if err := json.Unmarshal(data, &m); err != nil {
		return ""
	}

	if v, ok := m["display_date"].(string); ok {
		return v
	}

	return ""
}

func writeJSONAtomic(path string, value any) error {
	tmp := path + ".tmp"

	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}

	if err := os.WriteFile(tmp, data, 0644); err != nil {
		return err
	}

	return os.Rename(tmp, path)
}

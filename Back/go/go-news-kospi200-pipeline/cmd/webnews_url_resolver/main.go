package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	stdhtml "html"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
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
	ResolvedAt    string `json:"resolved_at"`
}

type CategoryResult struct {
	Category        string `json:"category"`
	OutputPath      string `json:"output_path"`
	SourceItemCount int    `json:"source_item_count"`
	WrittenCount    int    `json:"written_count"`
	SuccessCount    int    `json:"success_count"`
	FailedCount     int    `json:"failed_count"`
}

type ResolveManifest struct {
	SchemaVersion string           `json:"schema_version"`
	DisplayDate   string           `json:"display_date,omitempty"`
	GeneratedAt   string           `json:"generated_at"`
	CurrentDir    string           `json:"current_dir"`
	OutputDir     string           `json:"output_dir"`
	MaxItems      int              `json:"max_items_per_category"`
	Results       []CategoryResult `json:"results"`
}

type googleDecodeParams struct {
	ArticleID string
	Signature string
	Timestamp string
}

func main() {
	currentDir := flag.String("current-dir", "data/webnews/current", "directory containing current category json files")
	outputDir := flag.String("output-dir", "data/webnews/current/llm_resolved", "directory to write category resolved jsonl files")
	maxItems := flag.Int("max-items-per-category", 10, "max items to resolve per category")
	timeoutSeconds := flag.Int("timeout-seconds", 10, "http timeout seconds")
	delayMs := flag.Int("delay-ms", 500, "delay between resolve requests in milliseconds")
	userAgent := flag.String("user-agent", "Mozilla/5.0 WP-Capstone-WebNewsBot/1.0", "http user-agent")
	flag.Parse()

	if err := os.MkdirAll(*outputDir, 0755); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] create output dir: %v\n", err)
		os.Exit(1)
	}

	displayDate := readDisplayDate(*currentDir)

	client := &http.Client{
		Timeout: time.Duration(*timeoutSeconds) * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 8 {
				return http.ErrUseLastResponse
			}
			return nil
		},
	}

	manifest := ResolveManifest{
		SchemaVersion: "webnews-url-resolve.v1",
		DisplayDate:   displayDate,
		GeneratedAt:   time.Now().Format(time.RFC3339),
		CurrentDir:    *currentDir,
		OutputDir:     *outputDir,
		MaxItems:      *maxItems,
		Results:       make([]CategoryResult, 0, len(categories)),
	}

	for _, category := range categories {
		result := processCategory(
			client,
			*currentDir,
			*outputDir,
			category,
			displayDate,
			*maxItems,
			time.Duration(*delayMs)*time.Millisecond,
			*userAgent,
		)

		manifest.Results = append(manifest.Results, result)

		fmt.Printf(
			"[url_resolver] category=%s source=%d written=%d ok=%d failed=%d output=%s\n",
			result.Category,
			result.SourceItemCount,
			result.WrittenCount,
			result.SuccessCount,
			result.FailedCount,
			result.OutputPath,
		)
	}

	if err := writeJSONAtomic(filepath.Join(*outputDir, "resolved.manifest.json"), manifest); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] write manifest: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[url_resolver] done")
}

func processCategory(
	client *http.Client,
	currentDir string,
	outputDir string,
	category string,
	displayDate string,
	maxItems int,
	delay time.Duration,
	userAgent string,
) CategoryResult {
	categoryPath := filepath.Join(currentDir, category+".json")
	outputPath := filepath.Join(outputDir, category+".resolved.jsonl")
	tmpPath := outputPath + ".tmp"

	items, err := loadItems(categoryPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[WARN] load category=%s path=%s err=%v\n", category, categoryPath, err)
		return CategoryResult{
			Category:   category,
			OutputPath: outputPath,
		}
	}

	f, err := os.Create(tmpPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[WARN] create output category=%s err=%v\n", category, err)
		return CategoryResult{
			Category:        category,
			OutputPath:      outputPath,
			SourceItemCount: len(items),
		}
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetEscapeHTML(false)

	result := CategoryResult{
		Category:        category,
		OutputPath:      outputPath,
		SourceItemCount: len(items),
	}

	limit := len(items)
	if maxItems > 0 && limit > maxItems {
		limit = maxItems
	}

	for i := 0; i < limit; i++ {
		item := items[i]

		rank := getInt(item, i+1, "rank", "order", "position", "index")
		itemID := getString(item, "id", "item_id", "itemId", "hash")
		title := getString(item, "title", "headline", "name")
		publisher := getString(item, "publisher", "source", "provider", "press", "outlet")
		publishedAt := getString(item, "published_at", "publishedAt", "published", "pub_date", "pubDate")
		googleURL := getString(item, "google_news_url", "googleNewsUrl", "url", "link")

		rec := ResolveRecord{
			ItemID:        itemID,
			DisplayDate:   displayDate,
			Category:      category,
			Rank:          rank,
			Title:         title,
			Publisher:     publisher,
			PublishedAt:   publishedAt,
			GoogleNewsURL: googleURL,
			ResolveStatus: "failed",
			ResolvedAt:    time.Now().Format(time.RFC3339),
		}

		if googleURL == "" {
			rec.Error = "missing_google_news_url"
			result.FailedCount++
		} else {
			resolvedURL, resolveErr := resolveGoogleNewsURL(client, googleURL, userAgent)
			if resolveErr != nil {
				rec.Error = resolveErr.Error()
				result.FailedCount++
			} else {
				rec.ResolvedURL = resolvedURL
				rec.ResolveStatus = "ok"
				result.SuccessCount++
			}
		}

		if err := enc.Encode(rec); err != nil {
			fmt.Fprintf(os.Stderr, "[WARN] write record category=%s item_id=%s err=%v\n", category, itemID, err)
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

func resolveGoogleNewsURL(client *http.Client, rawURL string, userAgent string) (string, error) {
	if rawURL == "" {
		return "", fmt.Errorf("missing_url")
	}

	if !isGoogleNewsURL(rawURL) {
		if isGoodArticleURL(rawURL) {
			return rawURL, nil
		}
		return "", fmt.Errorf("not_article_url")
	}

	articleID, err := extractGoogleNewsArticleID(rawURL)
	if err != nil {
		return "", err
	}

	// 1차: 예전 Google News RSS URL은 base64 안에 원문 URL이 직접 들어있다.
	if decoded, err := decodeOldStyleGoogleNewsURL(articleID); err == nil && isGoodArticleURL(decoded) {
		return decoded, nil
	}

	// 2차: 2024년 이후 스타일은 Google batchexecute/garturlreq 방식으로 resolve한다.
	params, err := getGoogleDecodeParams(client, articleID, userAgent)
	if err != nil {
		return "", err
	}

	decoded, err := decodeByBatchExecute(client, params, userAgent)
	if err != nil {
		return "", err
	}

	if !isGoodArticleURL(decoded) {
		return "", fmt.Errorf("decoded_url_not_article")
	}

	return decoded, nil
}

func extractGoogleNewsArticleID(rawURL string) (string, error) {
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return "", fmt.Errorf("invalid_google_news_url")
	}

	parts := strings.Split(strings.Trim(parsed.Path, "/"), "/")
	if len(parts) < 2 {
		return "", fmt.Errorf("invalid_google_news_path")
	}

	for i := len(parts) - 1; i >= 0; i-- {
		if parts[i] == "" {
			continue
		}

		if parts[i] == "articles" || parts[i] == "read" {
			continue
		}

		return parts[i], nil
	}

	return "", fmt.Errorf("missing_google_news_article_id")
}

func decodeOldStyleGoogleNewsURL(articleID string) (string, error) {
	raw, err := base64.RawURLEncoding.DecodeString(articleID)
	if err != nil {
		raw, err = base64.URLEncoding.DecodeString(articleID)
		if err != nil {
			return "", fmt.Errorf("old_base64_decode_failed")
		}
	}

	prefix := []byte{0x08, 0x13, 0x22}
	if bytes.HasPrefix(raw, prefix) {
		raw = raw[len(prefix):]
	}

	suffix := []byte{0xd2, 0x01, 0x00}
	if bytes.HasSuffix(raw, suffix) {
		raw = raw[:len(raw)-len(suffix)]
	}

	if len(raw) < 2 {
		return "", fmt.Errorf("old_payload_too_short")
	}

	offset := 1
	length := int(raw[0])

	if raw[0] >= 0x80 {
		if len(raw) < 3 {
			return "", fmt.Errorf("old_length_payload_too_short")
		}
		offset = 2
		length = int(raw[1])
	}

	if offset+length > len(raw) {
		return "", fmt.Errorf("old_length_out_of_range")
	}

	candidate := string(raw[offset : offset+length])
	candidate = strings.TrimSpace(candidate)

	if strings.HasPrefix(candidate, "AU_yqL") {
		return "", fmt.Errorf("new_style_google_news_encoding")
	}

	if !isGoodArticleURL(candidate) {
		return "", fmt.Errorf("old_decoded_not_article_url")
	}

	return candidate, nil
}

func getGoogleDecodeParams(client *http.Client, articleID string, userAgent string) (googleDecodeParams, error) {
	candidates := []string{
		"https://news.google.com/articles/" + articleID,
		"https://news.google.com/rss/articles/" + articleID,
	}

	var lastErr error

	for _, targetURL := range candidates {
		req, err := http.NewRequest(http.MethodGet, targetURL, nil)
		if err != nil {
			lastErr = fmt.Errorf("decode_param_request_create_failed")
			continue
		}

		setGoogleHeaders(req, userAgent)

		resp, err := client.Do(req)
		if err != nil {
			lastErr = fmt.Errorf("decode_param_request_failed")
			continue
		}

		raw, readErr := io.ReadAll(io.LimitReader(resp.Body, 2*1024*1024))
		resp.Body.Close()

		if resp.StatusCode < 200 || resp.StatusCode >= 400 {
			lastErr = fmt.Errorf("decode_param_http_status_%d", resp.StatusCode)
			continue
		}

		if readErr != nil {
			lastErr = fmt.Errorf("decode_param_read_failed")
			continue
		}

		htmlText := string(raw)

		signature := extractAttr(htmlText, "data-n-a-sg")
		timestamp := extractAttr(htmlText, "data-n-a-ts")

		if signature != "" && timestamp != "" {
			return googleDecodeParams{
				ArticleID: articleID,
				Signature: signature,
				Timestamp: timestamp,
			}, nil
		}

		lastErr = fmt.Errorf("decode_params_not_found")
	}

	if lastErr == nil {
		lastErr = fmt.Errorf("decode_params_not_found")
	}

	return googleDecodeParams{}, lastErr
}

func decodeByBatchExecute(client *http.Client, params googleDecodeParams, userAgent string) (string, error) {
	inner := fmt.Sprintf(
		`["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"%s",%s,"%s"]`,
		escapeJSONString(params.ArticleID),
		params.Timestamp,
		escapeJSONString(params.Signature),
	)

	payloadValue := []any{
		[]any{
			[]any{
				"Fbv4je",
				inner,
			},
		},
	}

	payloadJSON, err := json.Marshal(payloadValue)
	if err != nil {
		return "", fmt.Errorf("batch_payload_marshal_failed")
	}

	form := url.Values{}
	form.Set("f.req", string(payloadJSON))

	req, err := http.NewRequest(
		http.MethodPost,
		"https://news.google.com/_/DotsSplashUi/data/batchexecute",
		strings.NewReader(form.Encode()),
	)
	if err != nil {
		return "", fmt.Errorf("batch_request_create_failed")
	}

	setGoogleHeaders(req, userAgent)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded;charset=UTF-8")
	req.Header.Set("Referer", "https://news.google.com/")

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("batch_request_failed")
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(io.LimitReader(resp.Body, 2*1024*1024))
	if err != nil {
		return "", fmt.Errorf("batch_read_failed")
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		return "", fmt.Errorf("batch_http_status_%d", resp.StatusCode)
	}

	decodedURL, err := extractDecodedURLFromBatchResponse(string(raw))
	if err != nil {
		return "", err
	}

	return decodedURL, nil
}

func extractDecodedURLFromBatchResponse(text string) (string, error) {
	// 가장 안정적인 파싱: batchexecute 응답의 JSON 라인에서 Fbv4je record를 찾고,
	// 그 record의 3번째 payload 문자열을 다시 JSON decode한다.
	lines := strings.Split(text, "\n")

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "[") || !strings.Contains(line, "Fbv4je") {
			continue
		}

		var outer []any
		if err := json.Unmarshal([]byte(line), &outer); err != nil {
			continue
		}

		for _, rawEntry := range outer {
			entry, ok := rawEntry.([]any)
			if !ok || len(entry) < 3 {
				continue
			}

			rpcID, _ := entry[1].(string)
			if rpcID != "Fbv4je" {
				continue
			}

			payload, ok := entry[2].(string)
			if !ok || payload == "" {
				continue
			}

			var inner []any
			if err := json.Unmarshal([]byte(payload), &inner); err != nil {
				continue
			}

			if len(inner) >= 2 {
				if kind, _ := inner[0].(string); kind == "garturlres" {
					if decoded, _ := inner[1].(string); decoded != "" {
						return stdhtml.UnescapeString(decoded), nil
					}
				}
			}
		}
	}

	// fallback: 응답 전체에서 garturlres 패턴 직접 추출
	re := regexp.MustCompile(`\\?"garturlres\\?",\\?"(https?://[^"\\]+)`)
	match := re.FindStringSubmatch(text)
	if len(match) >= 2 {
		candidate := strings.ReplaceAll(match[1], `\/`, `/`)
		candidate = stdhtml.UnescapeString(candidate)
		return candidate, nil
	}

	return "", fmt.Errorf("batch_decoded_url_not_found")
}

func loadItems(path string) ([]map[string]any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var root any
	if err := json.Unmarshal(data, &root); err != nil {
		return nil, err
	}

	return extractItems(root), nil
}

func extractItems(root any) []map[string]any {
	switch v := root.(type) {
	case []any:
		return anySliceToMapSlice(v)

	case map[string]any:
		for _, key := range []string{"items", "news", "articles", "data", "results"} {
			if arr, ok := v[key].([]any); ok {
				return anySliceToMapSlice(arr)
			}
		}
	}

	return nil
}

func anySliceToMapSlice(arr []any) []map[string]any {
	out := make([]map[string]any, 0, len(arr))
	for _, raw := range arr {
		if m, ok := raw.(map[string]any); ok {
			out = append(out, m)
		}
	}
	return out
}

func setGoogleHeaders(req *http.Request, userAgent string) {
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "*/*")
	req.Header.Set("Accept-Language", "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7")
	req.Header.Set("Cache-Control", "no-cache")
}

func extractAttr(htmlText string, attrName string) string {
	pattern := regexp.MustCompile(regexp.QuoteMeta(attrName) + `="([^"]+)"`)
	match := pattern.FindStringSubmatch(htmlText)
	if len(match) >= 2 {
		return stdhtml.UnescapeString(match[1])
	}

	patternSingle := regexp.MustCompile(regexp.QuoteMeta(attrName) + `='([^']+)'`)
	match = patternSingle.FindStringSubmatch(htmlText)
	if len(match) >= 2 {
		return stdhtml.UnescapeString(match[1])
	}

	return ""
}

func isGoogleNewsURL(rawURL string) bool {
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return false
	}

	host := strings.ToLower(parsed.Host)
	return host == "news.google.com" || strings.HasSuffix(host, ".news.google.com")
}

func isGoodArticleURL(rawURL string) bool {
	if rawURL == "" {
		return false
	}

	parsed, err := url.Parse(rawURL)
	if err != nil {
		return false
	}

	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return false
	}

	host := strings.ToLower(parsed.Host)
	path := strings.ToLower(parsed.Path)
	query := strings.ToLower(parsed.RawQuery)

	blockedHosts := []string{
		"google.com",
		"news.google.com",
		"www.google.com",
		"accounts.google.com",
		"policies.google.com",
		"support.google.com",

		"googleapis.com",
		"fonts.googleapis.com",
		"ajax.googleapis.com",

		"google-analytics.com",
		"www.google-analytics.com",
		"googletagmanager.com",
		"www.googletagmanager.com",
		"googlesyndication.com",
		"pagead2.googlesyndication.com",
		"doubleclick.net",
		"stats.g.doubleclick.net",

		"gstatic.com",
		"www.gstatic.com",
		"fonts.gstatic.com",
		"googleusercontent.com",
		"schema.org",
		"w3.org",
	}

	for _, blocked := range blockedHosts {
		if host == blocked || strings.HasSuffix(host, "."+blocked) {
			return false
		}
	}

	blockedHints := []string{
		".js",
		".css",
		".woff",
		".woff2",
		".ttf",
		".otf",
		".map",
		".ico",
		".png",
		".jpg",
		".jpeg",
		".webp",
		".gif",
		".svg",
		"analytics",
		"gtag",
		"collect",
		"ads",
		"pagead",
		"favicon",
	}

	for _, hint := range blockedHints {
		if strings.Contains(path, hint) || strings.Contains(query, hint) {
			return false
		}
	}

	return true
}

func escapeJSONString(s string) string {
	b, _ := json.Marshal(s)
	quoted := string(b)
	return strings.TrimPrefix(strings.TrimSuffix(quoted, `"`), `"`)
}

func getString(m map[string]any, keys ...string) string {
	for _, key := range keys {
		raw, ok := m[key]
		if !ok || raw == nil {
			continue
		}

		switch v := raw.(type) {
		case string:
			return strings.TrimSpace(v)
		case float64:
			return strconv.FormatFloat(v, 'f', -1, 64)
		case int:
			return strconv.Itoa(v)
		case map[string]any:
			nested := getString(v, "name", "title", "source", "publisher", "url", "link")
			if nested != "" {
				return nested
			}
		}
	}

	return ""
}

func getInt(m map[string]any, fallback int, keys ...string) int {
	for _, key := range keys {
		raw, ok := m[key]
		if !ok || raw == nil {
			continue
		}

		switch v := raw.(type) {
		case float64:
			return int(v)
		case int:
			return v
		case string:
			parsed, err := strconv.Atoi(strings.TrimSpace(v))
			if err == nil {
				return parsed
			}
		}
	}

	return fallback
}

func readDisplayDate(currentDir string) string {
	path := filepath.Join(currentDir, "manifest.json")

	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}

	var m map[string]any
	if err := json.Unmarshal(data, &m); err != nil {
		return ""
	}

	return getString(m, "display_date", "displayDate")
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

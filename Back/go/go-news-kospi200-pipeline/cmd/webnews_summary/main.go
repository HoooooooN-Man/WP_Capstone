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
)

var categories = []string{
	"korea",
	"world",
	"business",
	"science_tech",
	"policy_finance",
	"industry_ai",
}

var categoryLabels = map[string]string{
	"korea":          "대한민국",
	"world":          "세계",
	"business":       "비즈니스",
	"science_tech":   "과학기술",
	"policy_finance": "정책금융",
	"industry_ai":    "산업AI",
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

type LLMInputItem struct {
	Rank          int    `json:"rank"`
	Title         string `json:"title"`
	Publisher     string `json:"publisher,omitempty"`
	PublishedAt   string `json:"published_at,omitempty"`
	GoogleNewsURL string `json:"google_news_url,omitempty"`
	ResolvedURL   string `json:"resolved_url,omitempty"`
	InputBasis    string `json:"input_basis"`
	BodyCharCount int    `json:"body_char_count"`
	BodyText      string `json:"body_text,omitempty"`
	FetchStatus   string `json:"fetch_status"`
	FetchError    string `json:"fetch_error,omitempty"`
}

type SummaryManifest struct {
	SchemaVersion string           `json:"schema_version"`
	DisplayDate   string           `json:"display_date,omitempty"`
	GeneratedAt   string           `json:"generated_at"`
	Model         string           `json:"model"`
	BodyDir       string           `json:"body_dir"`
	SummaryDir    string           `json:"summary_dir"`
	Results       []CategoryResult `json:"results"`
}

type CategoryResult struct {
	Category          string `json:"category"`
	OutputPath        string `json:"output_path"`
	SourceItemCount   int    `json:"source_item_count"`
	UsableBodyCount   int    `json:"usable_body_count"`
	FallbackItemCount int    `json:"fallback_item_count"`
	Status            string `json:"status"`
	Error             string `json:"error,omitempty"`
}

type GeminiRequest struct {
	SystemInstruction GeminiSystemInstruction `json:"systemInstruction,omitempty"`
	Contents          []GeminiContent         `json:"contents"`
	GenerationConfig  GeminiGenerationConfig  `json:"generationConfig,omitempty"`
}

type GeminiSystemInstruction struct {
	Parts []GeminiPart `json:"parts"`
}

type GeminiContent struct {
	Role  string       `json:"role,omitempty"`
	Parts []GeminiPart `json:"parts"`
}

type GeminiPart struct {
	Text string `json:"text"`
}

type GeminiGenerationConfig struct {
	Temperature      float64 `json:"temperature,omitempty"`
	ResponseMIMEType string  `json:"responseMimeType,omitempty"`
}

type GeminiResponse struct {
	Candidates []struct {
		Content struct {
			Parts []struct {
				Text string `json:"text"`
			} `json:"parts"`
		} `json:"content"`
	} `json:"candidates"`
	Error *struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
		Status  string `json:"status"`
	} `json:"error,omitempty"`
}

func main() {
	bodyDir := flag.String("body-dir", "data/webnews/current/llm_input", "directory containing category body jsonl files")
	summaryDir := flag.String("summary-dir", "data/webnews/current/summaries", "directory to write category summary json files")
	model := flag.String("model", getenvDefault("GEMINI_MODEL", "gemini-3.5-flash"), "Gemini model name")
	minBodyChars := flag.Int("min-body-chars", getenvIntDefault("WEBNEWS_SUMMARY_MIN_BODY_CHARS", 500), "minimum body chars to treat as usable article body")
	maxBodyCharsPerItem := flag.Int("max-body-chars-per-item", getenvIntDefault("WEBNEWS_SUMMARY_MAX_BODY_CHARS_PER_ITEM", 1800), "max body chars per item sent to Gemini")
	timeoutSeconds := flag.Int("timeout-seconds", 60, "Gemini API timeout seconds")
	delayMs := flag.Int("delay-ms", 1000, "delay between Gemini requests")
	flag.Parse()

	apiKey := strings.TrimSpace(os.Getenv("GEMINI_API_KEY"))
	if apiKey == "" {
		fmt.Fprintln(os.Stderr, "[ERROR] GEMINI_API_KEY is empty. Load configs/llm.env first.")
		os.Exit(1)
	}

	if err := os.MkdirAll(*summaryDir, 0755); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] create summary dir: %v\n", err)
		os.Exit(1)
	}

	displayDate := readDisplayDateFromBodyManifest(*bodyDir)

	client := &http.Client{
		Timeout: time.Duration(*timeoutSeconds) * time.Second,
	}

	manifest := SummaryManifest{
		SchemaVersion: "webnews-summary-manifest.v1",
		DisplayDate:   displayDate,
		GeneratedAt:   time.Now().Format(time.RFC3339),
		Model:         *model,
		BodyDir:       *bodyDir,
		SummaryDir:    *summaryDir,
		Results:       make([]CategoryResult, 0, len(categories)),
	}

	for _, category := range categories {
		result := processCategory(
			client,
			apiKey,
			*model,
			*bodyDir,
			*summaryDir,
			category,
			displayDate,
			*minBodyChars,
			*maxBodyCharsPerItem,
		)

		manifest.Results = append(manifest.Results, result)

		fmt.Printf(
			"[summary] category=%s status=%s source=%d usable_body=%d fallback=%d output=%s",
			result.Category,
			result.Status,
			result.SourceItemCount,
			result.UsableBodyCount,
			result.FallbackItemCount,
			result.OutputPath,
		)
		if result.Error != "" {
			fmt.Printf(" error=%s", result.Error)
		}
		fmt.Println()

		if *delayMs > 0 {
			time.Sleep(time.Duration(*delayMs) * time.Millisecond)
		}
	}

	if err := writeJSONAtomic(filepath.Join(*summaryDir, "summary.manifest.json"), manifest); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] write summary manifest: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[summary] done")
}

func processCategory(
	client *http.Client,
	apiKey string,
	model string,
	bodyDir string,
	summaryDir string,
	category string,
	displayDate string,
	minBodyChars int,
	maxBodyCharsPerItem int,
) CategoryResult {
	inputPath := filepath.Join(bodyDir, category+".body.jsonl")
	outputPath := filepath.Join(summaryDir, category+".summary.json")

	rows, err := loadBodyJSONL(inputPath)
	if err != nil {
		writeFallbackSummary(outputPath, category, displayDate, model, nil, 0, 0, "load_body_failed:"+err.Error())
		return CategoryResult{
			Category:   category,
			OutputPath: outputPath,
			Status:     "failed",
			Error:      "load_body_failed",
		}
	}

	items := make([]LLMInputItem, 0, len(rows))
	usableBodyCount := 0
	fallbackCount := 0

	for _, row := range rows {
		item := LLMInputItem{
			Rank:          row.Rank,
			Title:         row.Title,
			Publisher:     row.Publisher,
			PublishedAt:   row.PublishedAt,
			GoogleNewsURL: row.GoogleNewsURL,
			ResolvedURL:   row.ResolvedURL,
			BodyCharCount: row.BodyCharCount,
			FetchStatus:   row.FetchStatus,
			FetchError:    row.Error,
		}

		if row.FetchStatus == "ok" && row.BodyCharCount >= minBodyChars {
			item.InputBasis = "article_body"
			item.BodyText = clipRunes(row.BodyText, maxBodyCharsPerItem)
			usableBodyCount++
		} else {
			item.InputBasis = "metadata_fallback"
			fallbackCount++
		}

		items = append(items, item)
	}

	prompt, err := buildPrompt(category, displayDate, items, minBodyChars)
	if err != nil {
		writeFallbackSummary(outputPath, category, displayDate, model, rows, usableBodyCount, fallbackCount, "build_prompt_failed")
		return CategoryResult{
			Category:          category,
			OutputPath:        outputPath,
			SourceItemCount:   len(rows),
			UsableBodyCount:   usableBodyCount,
			FallbackItemCount: fallbackCount,
			Status:            "failed",
			Error:             "build_prompt_failed",
		}
	}

	rawText, err := callGemini(client, apiKey, model, systemInstruction(), prompt)
	if err != nil {
		writeFallbackSummary(outputPath, category, displayDate, model, rows, usableBodyCount, fallbackCount, "gemini_failed:"+err.Error())
		return CategoryResult{
			Category:          category,
			OutputPath:        outputPath,
			SourceItemCount:   len(rows),
			UsableBodyCount:   usableBodyCount,
			FallbackItemCount: fallbackCount,
			Status:            "failed",
			Error:             "gemini_failed",
		}
	}

	cleaned := extractJSONObject(rawText)
	if !json.Valid([]byte(cleaned)) {
		writeFallbackSummary(outputPath, category, displayDate, model, rows, usableBodyCount, fallbackCount, "invalid_json_response")
		return CategoryResult{
			Category:          category,
			OutputPath:        outputPath,
			SourceItemCount:   len(rows),
			UsableBodyCount:   usableBodyCount,
			FallbackItemCount: fallbackCount,
			Status:            "failed",
			Error:             "invalid_json_response",
		}
	}

	var summary map[string]any
	if err := json.Unmarshal([]byte(cleaned), &summary); err != nil {
		writeFallbackSummary(outputPath, category, displayDate, model, rows, usableBodyCount, fallbackCount, "json_unmarshal_failed")
		return CategoryResult{
			Category:          category,
			OutputPath:        outputPath,
			SourceItemCount:   len(rows),
			UsableBodyCount:   usableBodyCount,
			FallbackItemCount: fallbackCount,
			Status:            "failed",
			Error:             "json_unmarshal_failed",
		}
	}

	// 모델 출력에 운영 메타데이터를 강제로 보강한다.
	summary["schema_version"] = "webnews-category-summary.v1"
	summary["status"] = "ok"
	summary["display_date"] = displayDate
	summary["category"] = category
	summary["category_label"] = categoryLabels[category]
	summary["generated_at"] = time.Now().Format(time.RFC3339)
	summary["model"] = model
	summary["source_item_count"] = len(rows)
	summary["usable_body_count"] = usableBodyCount
	summary["fallback_item_count"] = fallbackCount
	summary["input_policy"] = fmt.Sprintf("body_char_count >= %d 기사만 본문 근거로 사용, 나머지는 제목/언론사/발행시각 중심 fallback", minBodyChars)

	if err := writeJSONAtomic(outputPath, summary); err != nil {
		return CategoryResult{
			Category:          category,
			OutputPath:        outputPath,
			SourceItemCount:   len(rows),
			UsableBodyCount:   usableBodyCount,
			FallbackItemCount: fallbackCount,
			Status:            "failed",
			Error:             "write_summary_failed",
		}
	}

	return CategoryResult{
		Category:          category,
		OutputPath:        outputPath,
		SourceItemCount:   len(rows),
		UsableBodyCount:   usableBodyCount,
		FallbackItemCount: fallbackCount,
		Status:            "ok",
	}
}

func systemInstruction() string {
	return `너는 한국 주식시장 서비스에 들어갈 분야별 뉴스 요약기다.

규칙:
- 입력 데이터는 Google News RSS 기반 기사 목록과 일부 기사 본문 추출 결과다.
- input_basis가 article_body인 기사는 body_text를 주요 근거로 사용할 수 있다.
- input_basis가 metadata_fallback인 기사는 body_text가 없거나 품질이 낮으므로 title, publisher, published_at만 근거로 사용하라.
- body_char_count가 짧은 본문은 관련기사/메뉴/댓글정책일 수 있으므로 본문 사실처럼 단정하지 마라.
- 입력에 없는 기업명, 수치, 정책명, 인과관계를 만들지 마라.
- 특정 종목 매수/매도 추천을 하지 마라.
- 출력은 한국어 JSON 객체 하나만 작성하라.
- 마크다운, 코드블록, 부가 설명은 출력하지 마라.`
}

func buildPrompt(category string, displayDate string, items []LLMInputItem, minBodyChars int) (string, error) {
	itemsJSON, err := json.MarshalIndent(items, "", "  ")
	if err != nil {
		return "", err
	}

	label := categoryLabels[category]
	if label == "" {
		label = category
	}

	prompt := fmt.Sprintf(`아래는 display_date=%s 기준 "%s" 분야의 Webnews 기사 데이터다.

입력 품질 기준:
- body_char_count >= %d 이고 input_basis="article_body"인 기사만 본문 기반으로 사용한다.
- input_basis="metadata_fallback"인 기사는 제목/언론사/발행시각만 참고한다.
- 본문이 짧거나 실패한 기사의 세부 내용을 지어내지 않는다.

목표:
1. 이 분야의 주요 뉴스 흐름을 2~4문장으로 요약한다.
2. 핵심 포인트를 3~5개 작성한다.
3. 주식시장 관점에서 영향이 있을 수 있는 키워드를 3~6개 뽑는다.
4. market_impact_note는 투자 조언이 아니라 시장 관찰 메모로 작성한다.
5. notable_items에는 요약에 실제로 영향을 준 기사 2~4개를 rank/title/publisher/reason 형태로 정리한다.
6. data_quality_notes에는 본문 기반 기사 수와 fallback 기사 수를 고려한 한계를 적는다.
7. risk_notes에는 반드시 "투자 조언이 아님"과 "본문 추출 실패/오염 가능성"을 포함한다.

반드시 아래 JSON 필드만 출력하라:
{
  "schema_version": "webnews-category-summary.v1",
  "status": "ok",
  "display_date": "%s",
  "category": "%s",
  "category_label": "%s",
  "summary": "2~4문장 요약",
  "key_points": ["핵심 포인트"],
  "market_keywords": ["키워드"],
  "market_impact_note": "시장 관찰 메모",
  "notable_items": [
    {
      "rank": 1,
      "title": "기사 제목",
      "publisher": "언론사",
      "reason": "요약에 반영한 이유"
    }
  ],
  "data_quality_notes": ["데이터 품질 관련 메모"],
  "risk_notes": ["투자 조언이 아님", "본문 추출 실패/오염 가능성"]
}

NEWS_ITEMS:
%s
`, displayDate, label, minBodyChars, displayDate, category, label, string(itemsJSON))

	return prompt, nil
}

func callGemini(client *http.Client, apiKey string, model string, system string, prompt string) (string, error) {
	endpoint := fmt.Sprintf(
		"https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s",
		model,
		apiKey,
	)

	reqBody := GeminiRequest{
		SystemInstruction: GeminiSystemInstruction{
			Parts: []GeminiPart{{Text: system}},
		},
		Contents: []GeminiContent{
			{
				Role:  "user",
				Parts: []GeminiPart{{Text: prompt}},
			},
		},
		GenerationConfig: GeminiGenerationConfig{
			Temperature:      0.2,
			ResponseMIMEType: "application/json",
		},
	}

	payload, err := json.Marshal(reqBody)
	if err != nil {
		return "", err
	}

	req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(payload))
	if err != nil {
		return "", err
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(io.LimitReader(resp.Body, 4*1024*1024))
	if err != nil {
		return "", err
	}

	var gemResp GeminiResponse
	_ = json.Unmarshal(raw, &gemResp)

	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		if gemResp.Error != nil {
			return "", fmt.Errorf("http_%d:%s", resp.StatusCode, gemResp.Error.Message)
		}
		return "", fmt.Errorf("http_%d:%s", resp.StatusCode, string(raw))
	}

	if gemResp.Error != nil {
		return "", fmt.Errorf(gemResp.Error.Message)
	}

	if len(gemResp.Candidates) == 0 ||
		len(gemResp.Candidates[0].Content.Parts) == 0 ||
		gemResp.Candidates[0].Content.Parts[0].Text == "" {
		return "", fmt.Errorf("empty_gemini_response")
	}

	return gemResp.Candidates[0].Content.Parts[0].Text, nil
}

func loadBodyJSONL(path string) ([]BodyRecord, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	lines := strings.Split(string(data), "\n")
	out := make([]BodyRecord, 0, len(lines))

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		var rec BodyRecord
		if err := json.Unmarshal([]byte(line), &rec); err != nil {
			return nil, err
		}

		out = append(out, rec)
	}

	return out, nil
}

func writeFallbackSummary(
	outputPath string,
	category string,
	displayDate string,
	model string,
	rows []BodyRecord,
	usableBodyCount int,
	fallbackCount int,
	reason string,
) {
	_ = os.MkdirAll(filepath.Dir(outputPath), 0755)

	notable := make([]map[string]any, 0, 3)
	for _, row := range rows {
		if len(notable) >= 3 {
			break
		}
		notable = append(notable, map[string]any{
			"rank":      row.Rank,
			"title":     row.Title,
			"publisher": row.Publisher,
			"reason":    "LLM 요약 실패로 원문 메타데이터만 보존",
		})
	}

	fallback := map[string]any{
		"schema_version":      "webnews-category-summary.v1",
		"status":              "failed",
		"display_date":        displayDate,
		"category":            category,
		"category_label":      categoryLabels[category],
		"generated_at":        time.Now().Format(time.RFC3339),
		"model":               model,
		"source_item_count":   len(rows),
		"usable_body_count":   usableBodyCount,
		"fallback_item_count": fallbackCount,
		"summary":             "LLM 요약 생성에 실패했습니다. 기사 목록은 유지되며, 제목 기반 fallback 처리가 필요합니다.",
		"key_points":          []string{},
		"market_keywords":     []string{},
		"market_impact_note":  "요약 생성 실패로 시장 영향 메모를 생성하지 못했습니다.",
		"notable_items":       notable,
		"data_quality_notes":  []string{reason},
		"risk_notes":          []string{"투자 조언이 아님", "본문 추출 실패/오염 가능성"},
		"error":               reason,
	}

	_ = writeJSONAtomic(outputPath, fallback)
}

func extractJSONObject(text string) string {
	s := strings.TrimSpace(text)

	if strings.HasPrefix(s, "```") {
		s = strings.TrimPrefix(s, "```json")
		s = strings.TrimPrefix(s, "```")
		s = strings.TrimSuffix(s, "```")
		s = strings.TrimSpace(s)
	}

	start := strings.Index(s, "{")
	end := strings.LastIndex(s, "}")

	if start >= 0 && end > start {
		return s[start : end+1]
	}

	return s
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

func getenvDefault(key string, fallback string) string {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return fallback
	}
	return v
}

func getenvIntDefault(key string, fallback int) int {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return fallback
	}

	var parsed int
	if _, err := fmt.Sscanf(v, "%d", &parsed); err != nil {
		return fallback
	}

	return parsed
}

func readDisplayDateFromBodyManifest(bodyDir string) string {
	path := filepath.Join(bodyDir, "articles_body.manifest.json")

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

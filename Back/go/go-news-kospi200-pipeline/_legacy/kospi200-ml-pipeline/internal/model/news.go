package model

import "time"

type CompanyAlias struct {
    Ticker          string   `json:"ticker"`
    CompanyNameKO   string   `json:"company_name_ko"`
    CompanyNameEN   string   `json:"company_name_en,omitempty"`
    Aliases         []string `json:"aliases"`
    NegativeAliases []string `json:"negative_aliases,omitempty"`
    SearchQueries   []string `json:"search_queries,omitempty"`
    Market          string   `json:"market,omitempty"`
    Sector          string   `json:"sector,omitempty"`
    IsActive        bool     `json:"is_active,omitempty"`
    MatchPriority   int      `json:"match_priority,omitempty"`
    Notes           string   `json:"notes,omitempty"`
}

type RawNewsEvent struct {
    NewsID      string    `json:"news_id"`
    Provider    string    `json:"provider"`
    Query       string    `json:"query"`
    Title       string    `json:"title"`
    SourceName  string    `json:"source_name,omitempty"`
    GoogleURL   string    `json:"google_url,omitempty"`
    ArticleURL  string    `json:"article_url,omitempty"`
    Snippet     string    `json:"snippet,omitempty"`
    PublishedAt time.Time `json:"published_at"`
    FetchedAt   time.Time `json:"fetched_at"`
}

type MatchedCompany struct {
    Ticker      string  `json:"ticker"`
    CompanyName string  `json:"company_name"`
    MatchType   string  `json:"match_type"`
    MatchScore  float64 `json:"match_score"`
}

type NormalizedNewsEvent struct {
    NewsID            string           `json:"news_id"`
    Provider          string           `json:"provider"`
    Query             string           `json:"query"`
    Title             string           `json:"title"`
    TitleNorm         string           `json:"title_norm"`
    TitleHash         string           `json:"title_hash"`
    SourceName        string           `json:"source_name,omitempty"`
    GoogleURL         string           `json:"google_url,omitempty"`
    ArticleURL        string           `json:"article_url,omitempty"`
    Snippet           string           `json:"snippet,omitempty"`
    PublishedAt       time.Time        `json:"published_at"`
    FetchedAt         time.Time        `json:"fetched_at"`
    Matched           []MatchedCompany `json:"matched"`
    UsedForML         bool             `json:"used_for_ml"`
    UsedForDigest     bool             `json:"used_for_digest"`
    IsMacroQuery      bool             `json:"is_macro_query,omitempty"`
    MLExclusionReason string           `json:"ml_exclusion_reason,omitempty"`
    SourceQualityTier string           `json:"source_quality_tier,omitempty"`
    SentimentLabel    string           `json:"sentiment_label,omitempty"`
    SentimentScore    float64          `json:"sentiment_score,omitempty"`
}

type BatchEnvelope struct {
    BatchID      string                `json:"batch_id"`
    CreatedAt    time.Time             `json:"created_at"`
    ItemCount    int                   `json:"item_count"`
    WindowStart  time.Time             `json:"window_start"`
    WindowEnd    time.Time             `json:"window_end"`
    Items        []NormalizedNewsEvent `json:"items"`
    BatchType    string                `json:"batch_type"`
    SourceStream string                `json:"source_stream"`
}

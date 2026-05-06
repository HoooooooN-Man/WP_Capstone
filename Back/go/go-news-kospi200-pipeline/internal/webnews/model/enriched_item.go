package model

type EnrichedNewsItem struct {
	ID            string `json:"id"`
	DisplayDate   string `json:"display_date"`
	CategoryID    string `json:"category_id"`
	CategoryLabel string `json:"category_label"`

	Title         string `json:"title"`
	Publisher     string `json:"publisher"`
	GoogleNewsURL string `json:"google_news_url"`

	// 아래 3개는 기존 코드 호환용으로만 잠시 남겨둠.
	// 이제 더 이상 채우지 않으며, 최종 JSON에도 포함하지 않는 방향으로 정리 예정.
	OriginURL    string `json:"origin_url,omitempty"`
	CanonicalURL string `json:"canonical_url,omitempty"`
	ImageURL     string `json:"image_url,omitempty"`

	PublishedAt string `json:"published_at"`
	CollectedAt string `json:"collected_at"`
	FirstSeenAt string `json:"first_seen_at"`
	LastSeenAt  string `json:"last_seen_at"`

	Source  string `json:"source"`
	Query   string `json:"query"`
	RawGUID string `json:"raw_guid"`

	BestRank   int     `json:"best_rank"`
	LatestRank int     `json:"latest_rank"`
	SeenCount  int     `json:"seen_count"`
	Score      float64 `json:"score"`
}

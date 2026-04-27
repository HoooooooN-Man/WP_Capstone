package model

type EnrichedNewsItem struct {
	ID            string `json:"id"`
	DisplayDate   string `json:"display_date"`
	CategoryID    string `json:"category_id"`
	CategoryLabel string `json:"category_label"`

	Title         string `json:"title"`
	Publisher     string `json:"publisher"`
	GoogleNewsURL string `json:"google_news_url"`
	OriginURL     string `json:"origin_url"`
	CanonicalURL  string `json:"canonical_url"`
	ImageURL      string `json:"image_url"`

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

	LinkSource  string `json:"link_source"`
	ImageSource string `json:"image_source"`
}

package model

type FinalizedNewsCard struct {
	Rank int `json:"rank"`

	ID string `json:"id"`

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

	SeenCount  int     `json:"seen_count"`
	BestRank   int     `json:"best_rank"`
	LatestRank int     `json:"latest_rank"`
	Score      float64 `json:"score"`

	Source string `json:"source"`
	Query  string `json:"query"`
}

type FinalizedCategoryFile struct {
	DisplayDate   string              `json:"display_date"`
	CategoryID    string              `json:"category_id"`
	CategoryLabel string              `json:"category_label"`
	WindowStart   string              `json:"window_start"`
	WindowEnd     string              `json:"window_end"`
	GeneratedAt   string              `json:"generated_at"`
	ItemCount     int                 `json:"item_count"`
	Items         []FinalizedNewsCard `json:"items"`
}

type FinalizeManifest struct {
	DisplayDate string   `json:"display_date"`
	WindowStart string   `json:"window_start"`
	WindowEnd   string   `json:"window_end"`
	GeneratedAt string   `json:"generated_at"`
	Categories  []string `json:"categories"`
	TopN        int      `json:"top_n"`
}

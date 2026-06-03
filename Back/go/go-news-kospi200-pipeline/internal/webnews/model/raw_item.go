package model

type RawNewsItem struct {
	DisplayDate   string `json:"display_date"`
	CategoryID    string `json:"category_id"`
	CategoryLabel string `json:"category_label"`
	Rank          int    `json:"rank"`
	Title         string `json:"title"`
	Publisher     string `json:"publisher"`
	GoogleNewsURL string `json:"google_news_url"`
	PublishedAt   string `json:"published_at,omitempty"`
	CollectedAt   string `json:"collected_at"`
	Source        string `json:"source"`
	Query         string `json:"query,omitempty"`
	RawGUID       string `json:"raw_guid,omitempty"`
}

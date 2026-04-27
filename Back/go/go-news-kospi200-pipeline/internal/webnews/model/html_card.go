package model

type HTMLNewsCard struct {
	DisplayDate   string `json:"display_date"`
	CategoryID    string `json:"category_id"`
	CategoryLabel string `json:"category_label"`

	CardRank int `json:"card_rank"`

	Title     string `json:"title"`
	Publisher string `json:"publisher"`

	GoogleNewsURL string `json:"google_news_url"`
	PossibleURL   string `json:"possible_url"`
	ThumbnailURL  string `json:"thumbnail_url"`

	CollectedAt string `json:"collected_at"`
	Query       string `json:"query"`
	Source      string `json:"source"`
}

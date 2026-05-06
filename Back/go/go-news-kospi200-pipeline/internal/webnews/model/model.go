package model

type CategoryConfig struct {
	ID      string `json:"id"`
	Label   string `json:"label"`
	Mode    string `json:"mode"`
	Source  string `json:"source"`
	FeedURL string `json:"feed_url,omitempty"`
	Query   string `json:"query,omitempty"`
	TopN    int    `json:"top_n"`
}

type CollectJob struct {
	DisplayDate   string `json:"display_date"`
	CategoryID    string `json:"category_id"`
	CategoryLabel string `json:"category_label"`
	Mode          string `json:"mode"`
	Source        string `json:"source"`
	FeedURL       string `json:"feed_url,omitempty"`
	Query         string `json:"query,omitempty"`
	TopN          int    `json:"top_n"`
	ScheduledAt   string `json:"scheduled_at"`
	WindowStart   string `json:"window_start"`
	WindowEnd     string `json:"window_end"`
}

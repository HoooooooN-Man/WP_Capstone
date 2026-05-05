package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
)

type Config struct {
	RedisPrefix               string
	DataDir                   string
	CategoriesFile            string
	Timezone                  string
	MarketOpenHour            int
	MarketOpenMinute          int
	TopN                      int
	CollectionIntervalMinutes int
	FetchTimeout              time.Duration
	EnrichConcurrency         int
	FinalizeAt                string
	PublishAt                 string
	KeepLastGood              bool
	UserAgent                 string
}

type categoryFile struct {
	Categories []model.CategoryConfig `json:"categories"`
}

func LoadFromEnv() (Config, error) {
	cfg := Config{
		RedisPrefix:               getenv("WEBNEWS_REDIS_PREFIX", "webnews"),
		DataDir:                   getenv("WEBNEWS_DATA_DIR", "./data/webnews"),
		CategoriesFile:            getenv("WEBNEWS_CATEGORIES_FILE", "./configs/webnews_categories.json"),
		Timezone:                  getenv("WEBNEWS_TIMEZONE", "Asia/Seoul"),
		MarketOpenHour:            mustInt(getenv("WEBNEWS_MARKET_OPEN_HOUR", "9")),
		MarketOpenMinute:          mustInt(getenv("WEBNEWS_MARKET_OPEN_MINUTE", "0")),
		TopN:                      mustInt(getenv("WEBNEWS_TOP_N", "10")),
		CollectionIntervalMinutes: mustInt(getenv("WEBNEWS_COLLECTION_INTERVAL_MINUTES", "15")),
		FetchTimeout:              mustDuration(getenv("WEBNEWS_FETCH_TIMEOUT_SECONDS", "10") + "s"),
		EnrichConcurrency:         mustInt(getenv("WEBNEWS_ENRICH_CONCURRENCY", "8")),
		FinalizeAt:                getenv("WEBNEWS_FINALIZE_AT", "08:55"),
		PublishAt:                 getenv("WEBNEWS_PUBLISH_AT", "08:58"),
		KeepLastGood:              getenv("WEBNEWS_KEEP_LAST_GOOD", "1") != "0",
		UserAgent:                 getenv("WEBNEWS_USER_AGENT", "Mozilla/5.0 WP-Capstone-WebNewsBot/1.0"),
	}

	if strings.TrimSpace(cfg.RedisPrefix) == "" {
		return Config{}, fmt.Errorf("WEBNEWS_REDIS_PREFIX is empty")
	}
	if strings.TrimSpace(cfg.CategoriesFile) == "" {
		return Config{}, fmt.Errorf("WEBNEWS_CATEGORIES_FILE is empty")
	}

	return cfg, nil
}

func LoadCategories(path string, defaultTopN int) ([]model.CategoryConfig, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read categories file: %w", err)
	}

	var parsed categoryFile
	if err := json.Unmarshal(b, &parsed); err != nil {
		return nil, fmt.Errorf("parse categories file: %w", err)
	}

	if len(parsed.Categories) == 0 {
		return nil, fmt.Errorf("no categories found in %s", path)
	}

	out := make([]model.CategoryConfig, 0, len(parsed.Categories))
	seen := map[string]struct{}{}

	for _, c := range parsed.Categories {
		c.ID = strings.TrimSpace(c.ID)
		c.Label = strings.TrimSpace(c.Label)
		c.Mode = strings.TrimSpace(c.Mode)
		c.Source = strings.TrimSpace(c.Source)
		c.FeedURL = strings.TrimSpace(c.FeedURL)
		c.Query = strings.TrimSpace(c.Query)

		if c.ID == "" {
			return nil, fmt.Errorf("category id is empty")
		}
		if _, exists := seen[c.ID]; exists {
			return nil, fmt.Errorf("duplicate category id: %s", c.ID)
		}
		seen[c.ID] = struct{}{}

		if c.Label == "" {
			c.Label = c.ID
		}
		if c.Mode == "" {
			c.Mode = "search"
		}
		if c.Source == "" {
			c.Source = "google_news"
		}
		if c.TopN <= 0 {
			c.TopN = defaultTopN
		}

		out = append(out, c)
	}

	return out, nil
}

func EnsureDataDirs(dataDir string) error {
	dirs := []string{
		filepath.Join(dataDir, "staging"),
		filepath.Join(dataDir, "current"),
		filepath.Join(dataDir, "archive"),
	}
	for _, dir := range dirs {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return fmt.Errorf("mkdir %s: %w", dir, err)
		}
	}
	return nil
}

func LoadLocation(name string) (*time.Location, error) {
	return time.LoadLocation(name)
}

func getenv(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func mustInt(s string) int {
	v, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil {
		panic(err)
	}
	return v
}

func mustDuration(s string) time.Duration {
	d, err := time.ParseDuration(strings.TrimSpace(s))
	if err != nil {
		panic(err)
	}
	return d
}

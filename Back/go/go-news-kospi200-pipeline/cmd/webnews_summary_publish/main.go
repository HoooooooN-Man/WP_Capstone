package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

var categories = []string{
	"korea",
	"world",
	"business",
	"science_tech",
	"policy_finance",
	"industry_ai",
}

func main() {
	currentDir := flag.String("current-dir", "data/webnews/current", "directory containing manifest.json")
	summaryDir := flag.String("summary-dir", "data/webnews/current/summaries", "directory containing category summary json files")
	envFile := flag.String("env-file", "configs/webnews.env", "env file containing Redis queue connection settings")
	keyPrefix := flag.String("key-prefix", "webnews", "Redis key prefix")
	ttlSeconds := flag.Int("ttl-seconds", 172800, "Redis TTL seconds; 0 means no expiration")
	dryRun := flag.Bool("dry-run", false, "print keys without writing Redis")
	flag.Parse()

	envMap := readEnvFile(*envFile)

	host := getConfigValue(envMap, "REDIS_QUEUE_HOST", "127.0.0.1")
	port := getConfigValue(envMap, "REDIS_QUEUE_PORT", "6379")
	password := getConfigValue(envMap, "REDIS_QUEUE_PASSWORD", "")
	db := parseInt(getConfigValue(envMap, "REDIS_QUEUE_DB", "0"), 0)

	displayDate := readDisplayDate(*currentDir, *summaryDir)
	if displayDate == "" {
		fmt.Fprintln(os.Stderr, "[ERROR] display_date not found from current manifest or summary manifest")
		os.Exit(1)
	}

	addr := host + ":" + port
	var ttl time.Duration
	if *ttlSeconds > 0 {
		ttl = time.Duration(*ttlSeconds) * time.Second
	}

	ctx := context.Background()

	var rdb *redis.Client
	if !*dryRun {
		rdb = redis.NewClient(&redis.Options{
			Addr:     addr,
			Password: password,
			DB:       db,
		})
		defer rdb.Close()

		if err := rdb.Ping(ctx).Err(); err != nil {
			fmt.Fprintf(os.Stderr, "[ERROR] redis ping failed addr=%s db=%d err=%v\n", addr, db, err)
			os.Exit(1)
		}
	}

	fmt.Printf("[summary_publish] display_date=%s redis=%s db=%d ttl_seconds=%d dry_run=%v\n", displayDate, addr, db, *ttlSeconds, *dryRun)

	okCount := 0
	failCount := 0

	for _, category := range categories {
		path := filepath.Join(*summaryDir, category+".summary.json")
		raw, err := os.ReadFile(path)
		if err != nil {
			fmt.Fprintf(os.Stderr, "[WARN] read summary failed category=%s path=%s err=%v\n", category, path, err)
			failCount++
			continue
		}

		if !json.Valid(raw) {
			fmt.Fprintf(os.Stderr, "[WARN] invalid json category=%s path=%s\n", category, path)
			failCount++
			continue
		}

		key := fmt.Sprintf("%s:%s:summary:%s", *keyPrefix, displayDate, category)

		if *dryRun {
			fmt.Printf("[summary_publish] dry-run key=%s bytes=%d\n", key, len(raw))
			okCount++
			continue
		}

		if err := rdb.Set(ctx, key, string(raw), ttl).Err(); err != nil {
			fmt.Fprintf(os.Stderr, "[WARN] redis set failed key=%s err=%v\n", key, err)
			failCount++
			continue
		}

		fmt.Printf("[summary_publish] set key=%s bytes=%d\n", key, len(raw))
		okCount++
	}

	if !*dryRun {
		updatedKey := fmt.Sprintf("%s:%s:summary:updated_at", *keyPrefix, displayDate)
		_ = rdb.Set(ctx, updatedKey, time.Now().Format(time.RFC3339), ttl).Err()
	}

	fmt.Printf("[summary_publish] done ok=%d failed=%d\n", okCount, failCount)

	if failCount > 0 {
		os.Exit(1)
	}
}

func readEnvFile(path string) map[string]string {
	out := map[string]string{}

	f, err := os.Open(path)
	if err != nil {
		return out
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		idx := strings.Index(line, "=")
		if idx <= 0 {
			continue
		}

		key := strings.TrimSpace(line[:idx])
		val := strings.TrimSpace(line[idx+1:])

		val = strings.Trim(val, `"'`)
		out[key] = val
	}

	return out
}

func getConfigValue(envMap map[string]string, key string, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}

	if v := strings.TrimSpace(envMap[key]); v != "" {
		return v
	}

	return fallback
}

func parseInt(s string, fallback int) int {
	v, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil {
		return fallback
	}
	return v
}

func readDisplayDate(currentDir string, summaryDir string) string {
	currentManifest := filepath.Join(currentDir, "manifest.json")
	if v := readDisplayDateFromJSON(currentManifest); v != "" {
		return v
	}

	summaryManifest := filepath.Join(summaryDir, "summary.manifest.json")
	if v := readDisplayDateFromJSON(summaryManifest); v != "" {
		return v
	}

	return ""
}

func readDisplayDateFromJSON(path string) string {
	raw, err := os.ReadFile(path)
	if err != nil {
		return ""
	}

	var m map[string]any
	if err := json.Unmarshal(raw, &m); err != nil {
		return ""
	}

	if v, ok := m["display_date"].(string); ok {
		return strings.TrimSpace(v)
	}

	return ""
}

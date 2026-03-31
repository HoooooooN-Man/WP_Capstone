package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	RedisAddr           string
	RedisPassword       string
	RedisDB             int
	RedisProtocol       int
	RawStream           string
	NormalizedStream    string
	BatchReadyStream    string
	RawGroup            string
	NormalizedGroup     string
	BatchGroup          string
	RawConsumer         string
	NormalizedConsumer  string
	BatchConsumer       string
	DedupPrefix         string
	UniversePath        string
	SourcePolicyPath    string
	Queries             []string
	RequestTimeout      time.Duration
	PollBlock           time.Duration
	BatchFlushInterval  time.Duration
	BatchMaxItems       int
	SpoolDir            string
	FrontWindowDuration time.Duration
}

func Load() Config {
	loadDotEnv()

	return Config{
		RedisAddr:           resolveRedisAddr(),
		RedisPassword:       firstNonEmpty("REDIS_QUEUE_PASSWORD", "REDIS_PASSWORD"),
		RedisDB:             mustAtoi(firstNonEmptyWithDefault("REDIS_QUEUE_DB", "REDIS_DB", "0")),
		RedisProtocol:       mustAtoi(firstNonEmptyWithDefault("REDIS_QUEUE_PROTOCOL", "REDIS_PROTOCOL", "2")),
		RawStream:           getenv("RAW_STREAM", "news:raw"),
		NormalizedStream:    getenv("NORMALIZED_STREAM", "news:normalized"),
		BatchReadyStream:    getenv("BATCH_READY_STREAM", "news:batch_ready"),
		RawGroup:            getenv("RAW_GROUP", "matcher-group"),
		NormalizedGroup:     getenv("NORMALIZED_GROUP", "aggregator-group"),
		BatchGroup:          getenv("BATCH_GROUP", "writer-group"),
		RawConsumer:         getenv("RAW_CONSUMER", hostnameOr("matcher-1")),
		NormalizedConsumer:  getenv("NORMALIZED_CONSUMER", hostnameOr("aggregator-1")),
		BatchConsumer:       getenv("BATCH_CONSUMER", hostnameOr("writer-1")),
		DedupPrefix:         getenv("DEDUP_PREFIX", "news:dedup"),
		UniversePath:        getenv("UNIVERSE_PATH", "data/universe/current/kospi200.aliases.current.json"),
		SourcePolicyPath:    getenv("SOURCE_POLICY_PATH", "data/policies/news_source_policy.current.json"),
		Queries:             splitCSV(getenv("NEWS_QUERIES", "삼성전자,SK하이닉스,현대차,코스피,반도체,금리,환율")),
		RequestTimeout:      mustDuration(getenv("REQUEST_TIMEOUT", "10s")),
		PollBlock:           mustDuration(getenv("POLL_BLOCK", "5s")),
		BatchFlushInterval:  mustDuration(getenv("BATCH_FLUSH_INTERVAL", "1m")),
		BatchMaxItems:       mustAtoi(getenv("BATCH_MAX_ITEMS", "100")),
		SpoolDir:            getenv("SPOOL_DIR", "./spool"),
		FrontWindowDuration: mustDuration(getenv("FRONT_WINDOW_DURATION", "2h")),
	}
}

func (c Config) RedisURL() string {
	return fmt.Sprintf("redis://%s", c.RedisAddr)
}

func resolveRedisAddr() string {
	if addr := firstNonEmpty("REDIS_QUEUE_ADDR", "REDIS_ADDR"); addr != "" {
		return addr
	}

	host := firstNonEmpty("REDIS_QUEUE_HOST", "REDIS_HOST")
	port := firstNonEmpty("REDIS_QUEUE_PORT", "REDIS_PORT")
	if host != "" {
		if port == "" {
			port = "6379"
		}
		return fmt.Sprintf("%s:%s", host, port)
	}

	return "localhost:6379"
}

func firstNonEmpty(keys ...string) string {
	for _, key := range keys {
		if v := strings.TrimSpace(os.Getenv(key)); v != "" {
			return v
		}
	}
	return ""
}

func firstNonEmptyWithDefault(primary, secondary, fallback string) string {
	if v := firstNonEmpty(primary, secondary); v != "" {
		return v
	}
	return fallback
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func mustAtoi(s string) int {
	v, err := strconv.Atoi(s)
	if err != nil {
		panic(err)
	}
	return v
}

func mustDuration(s string) time.Duration {
	d, err := time.ParseDuration(s)
	if err != nil {
		panic(err)
	}
	return d
}

func splitCSV(s string) []string {
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

func hostnameOr(fallback string) string {
	name, err := os.Hostname()
	if err != nil || name == "" {
		return fallback
	}
	return name
}

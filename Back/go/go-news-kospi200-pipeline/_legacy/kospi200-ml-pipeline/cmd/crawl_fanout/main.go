package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/planner"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/rss"
	"github.com/redis/go-redis/v9"
)

type runtimeConfig struct {
	QueryPlanPath string
	Workers       int
	JobDelay      time.Duration
	FetchTimeout  time.Duration
	MaxJobs       int
}

type crawlResult struct {
	Job       planner.QueryJob
	Fetched   int
	Pushed    int
	Failed    bool
	Err       error
	StartedAt time.Time
	EndedAt   time.Time
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	rt := loadRuntimeConfig(cfg)

	plan, err := planner.Load(rt.QueryPlanPath)
	if err != nil {
		log.Fatalf("crawl_fanout: failed to load query plan: %v", err)
	}

	jobs := plan.Jobs
	if rt.MaxJobs > 0 && rt.MaxJobs < len(jobs) {
		jobs = jobs[:rt.MaxJobs]
	}

	client := redisx.NewClient(cfg)
	if err := redisx.Ping(ctx, client); err != nil {
		log.Fatalf("crawl_fanout: redis ping failed: %v", err)
	}

	rssClient := rss.NewGoogleNewsClient()

	log.Printf("crawl_fanout: start plan=%s as_of_date=%s jobs=%d workers=%d raw_stream=%s", rt.QueryPlanPath, plan.AsOfDate, len(jobs), rt.Workers, cfg.RawStream)

	jobCh := make(chan planner.QueryJob)
	resultCh := make(chan crawlResult, len(jobs))

	var wg sync.WaitGroup
	for i := 0; i < rt.Workers; i++ {
		wg.Add(1)
		workerID := i + 1
		go func() {
			defer wg.Done()
			for job := range jobCh {
				resultCh <- runJob(ctx, client, cfg, rt, rssClient, workerID, job)
			}
		}()
	}

	go func() {
		defer close(jobCh)
		for _, job := range jobs {
			select {
			case <-ctx.Done():
				return
			case jobCh <- job:
			}
		}
	}()

	go func() {
		wg.Wait()
		close(resultCh)
	}()

	var totalFetched int64
	var totalPushed int64
	var totalFailed int64
	var companyJobs int64
	var macroJobs int64

	for res := range resultCh {
		switch res.Job.JobType {
		case "company":
			atomic.AddInt64(&companyJobs, 1)
		case "macro":
			atomic.AddInt64(&macroJobs, 1)
		}

		if res.Failed {
			atomic.AddInt64(&totalFailed, 1)
			log.Printf("crawl_fanout: FAIL job_id=%s type=%s ticker=%s query=%q err=%v", res.Job.JobID, res.Job.JobType, res.Job.Ticker, res.Job.Query, res.Err)
			continue
		}

		atomic.AddInt64(&totalFetched, int64(res.Fetched))
		atomic.AddInt64(&totalPushed, int64(res.Pushed))
		log.Printf("crawl_fanout: OK job_id=%s type=%s ticker=%s query=%q fetched=%d pushed=%d duration=%s", res.Job.JobID, res.Job.JobType, res.Job.Ticker, res.Job.Query, res.Fetched, res.Pushed, res.EndedAt.Sub(res.StartedAt))
	}

	log.Printf(
		"crawl_fanout: completed jobs=%d company_jobs=%d macro_jobs=%d total_fetched=%d total_pushed=%d total_failed=%d",
		len(jobs),
		companyJobs,
		macroJobs,
		totalFetched,
		totalPushed,
		totalFailed,
	)
}

func loadRuntimeConfig(cfg config.Config) runtimeConfig {
	workers := getenvInt("CRAWL_WORKERS", 6)
	if workers <= 0 {
		workers = 1
	}

	jobDelay := getenvDuration("CRAWL_JOB_DELAY", 250*time.Millisecond)
	fetchTimeout := getenvDuration("CRAWL_FETCH_TIMEOUT", cfg.RequestTimeout)
	if fetchTimeout <= 0 {
		fetchTimeout = 10 * time.Second
	}

	return runtimeConfig{
		QueryPlanPath: getenvString("QUERY_PLAN_PATH", "data/plans/current/query-plan.current.json"),
		Workers:       workers,
		JobDelay:      jobDelay,
		FetchTimeout:  fetchTimeout,
		MaxJobs:       getenvInt("CRAWL_MAX_JOBS", 0),
	}
}

func runJob(parent context.Context, client *redis.Client, cfg config.Config, rt runtimeConfig, rssClient *rss.GoogleNewsClient, workerID int, job planner.QueryJob) crawlResult {
	started := time.Now()
	result := crawlResult{Job: job, StartedAt: started}

	if rt.JobDelay > 0 {
		select {
		case <-parent.Done():
			result.Failed = true
			result.Err = parent.Err()
			result.EndedAt = time.Now()
			return result
		case <-time.After(rt.JobDelay):
		}
	}

	ctx, cancel := context.WithTimeout(parent, rt.FetchTimeout)
	defer cancel()

	items, err := rssClient.Fetch(ctx, job.Query)
	if err != nil {
		result.Failed = true
		result.Err = err
		result.EndedAt = time.Now()
		return result
	}

	result.Fetched = len(items)

	for _, item := range items {
		item.Query = job.Query
		if _, err := redisx.AddJSON(parent, client, cfg.RawStream, item, 200000); err != nil {
			log.Printf("crawl_fanout: push failed worker=%d job_id=%s query=%q news_id=%s err=%v", workerID, job.JobID, job.Query, item.NewsID, err)
			continue
		}
		result.Pushed++
	}

	result.EndedAt = time.Now()
	return result
}

func getenvString(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getenvInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(v)
	if err != nil {
		return fallback
	}
	return parsed
}

func getenvDuration(key string, fallback time.Duration) time.Duration {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	parsed, err := time.ParseDuration(v)
	if err != nil {
		return fallback
	}
	return parsed
}

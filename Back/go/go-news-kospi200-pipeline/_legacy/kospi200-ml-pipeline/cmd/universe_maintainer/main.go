package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type MetadataFile struct {
	AsOfDate string `json:"as_of_date"`
}

func main() {
	var (
		rootDir  = flag.String("root", "data/universe", "universe root directory")
		asOfDate = flag.String("as-of-date", "", "snapshot date in YYYY-MM-DD format; defaults to aliases current file or today")
		retDays  = flag.Int("retain-days", 30, "number of daily archive days to retain")
	)
	flag.Parse()

	date, err := resolveAsOfDate(*rootDir, *asOfDate)
	if err != nil {
		fmt.Fprintf(os.Stderr, "resolve as-of-date: %v\n", err)
		os.Exit(1)
	}

	if err := snapshot(*rootDir, date, *retDays); err != nil {
		fmt.Fprintf(os.Stderr, "snapshot failed: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("universe snapshot completed for %s\n", date.Format("2006-01-02"))
}

func resolveAsOfDate(root, input string) (time.Time, error) {
	if strings.TrimSpace(input) != "" {
		return time.Parse("2006-01-02", input)
	}

	aliasPath := filepath.Join(root, "current", "kospi200.aliases.current.json")
	b, err := os.ReadFile(aliasPath)
	if err == nil {
		var meta MetadataFile
		if json.Unmarshal(b, &meta) == nil && strings.TrimSpace(meta.AsOfDate) != "" {
			return time.Parse("2006-01-02", meta.AsOfDate)
		}
	}

	now := time.Now()
	return time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location()), nil
}

func snapshot(root string, asOfDate time.Time, retainDays int) error {
	currentDir := filepath.Join(root, "current")
	dailyDir := filepath.Join(root, "archive", asOfDate.Format("2006-01-02"))
	monthlyDir := filepath.Join(root, "archive-monthly", asOfDate.Format("2006-01"))

	if err := os.MkdirAll(dailyDir, 0o755); err != nil {
		return err
	}
	if err := os.MkdirAll(monthlyDir, 0o755); err != nil {
		return err
	}

	files := []string{
		"kospi200.constituents.current.json",
		"kospi200.aliases.current.json",
		"kospi200.match_rules.current.json",
	}

	for _, currentName := range files {
		src := filepath.Join(currentDir, currentName)
		basePrefix := strings.TrimSuffix(currentName, ".current.json")
		dailyName := fmt.Sprintf("%s.%s.json", basePrefix, asOfDate.Format("2006-01-02"))
		if err := copyFile(src, filepath.Join(dailyDir, dailyName)); err != nil {
			return err
		}
		if isMonthEnd(asOfDate) {
			if err := copyFile(src, filepath.Join(monthlyDir, dailyName)); err != nil {
				return err
			}
		}
	}

	return pruneDailyArchive(filepath.Join(root, "archive"), asOfDate, retainDays)
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	if _, err := io.Copy(out, in); err != nil {
		return err
	}
	return out.Sync()
}

func isMonthEnd(t time.Time) bool {
	return t.AddDate(0, 0, 1).Month() != t.Month()
}

func pruneDailyArchive(archiveRoot string, asOfDate time.Time, retainDays int) error {
	entries, err := os.ReadDir(archiveRoot)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	cutoff := asOfDate.AddDate(0, 0, -(retainDays - 1))
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		name := entry.Name()
		d, err := time.Parse("2006-01-02", name)
		if err != nil {
			continue
		}
		if d.Before(cutoff) {
			if err := os.RemoveAll(filepath.Join(archiveRoot, name)); err != nil {
				return err
			}
		}
	}
	return nil
}

func listDailySnapshots(archiveRoot string) ([]string, error) {
	entries, err := os.ReadDir(archiveRoot)
	if err != nil {
		return nil, err
	}
	var dates []string
	for _, entry := range entries {
		if entry.IsDir() {
			dates = append(dates, entry.Name())
		}
	}
	sort.Strings(dates)
	return dates, nil
}

package publisher

import (
	"fmt"
	"os"
	"path/filepath"
	"time"
)

type SwapResult struct {
	CurrentDir string
	BackupDir  string
}

func PublishStagingToCurrent(dataDir, displayDate string, keepLastGood bool) (SwapResult, error) {
	stagingDir := filepath.Join(dataDir, "staging", displayDate)
	currentDir := filepath.Join(dataDir, "current")
	archiveRoot := filepath.Join(dataDir, "archive")

	if _, err := os.Stat(stagingDir); err != nil {
		return SwapResult{}, fmt.Errorf("staging dir not found: %w", err)
	}

	if err := os.MkdirAll(archiveRoot, 0o755); err != nil {
		return SwapResult{}, fmt.Errorf("mkdir archive root: %w", err)
	}

	backupDir := ""
	if exists(currentDir) {
		if keepLastGood {
			backupDir = filepath.Join(
				archiveRoot,
				"current-"+time.Now().Format("20060102T150405"),
			)

			if err := os.RemoveAll(backupDir); err != nil {
				return SwapResult{}, fmt.Errorf("remove existing backup dir: %w", err)
			}
			if err := os.Rename(currentDir, backupDir); err != nil {
				return SwapResult{}, fmt.Errorf("move current to backup: %w", err)
			}
		} else {
			if err := os.RemoveAll(currentDir); err != nil {
				return SwapResult{}, fmt.Errorf("remove current dir: %w", err)
			}
		}
	}

	if err := os.Rename(stagingDir, currentDir); err != nil {
		if backupDir != "" && !exists(currentDir) && exists(backupDir) {
			_ = os.Rename(backupDir, currentDir)
		}
		return SwapResult{}, fmt.Errorf("move staging to current: %w", err)
	}

	return SwapResult{
		CurrentDir: currentDir,
		BackupDir:  backupDir,
	}, nil
}

func exists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

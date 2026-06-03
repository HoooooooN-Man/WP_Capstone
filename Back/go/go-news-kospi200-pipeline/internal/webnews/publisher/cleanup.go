package publisher

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
)

func CleanupArchiveDirs(archiveRoot string, keepLastGood bool) error {
	if err := os.MkdirAll(archiveRoot, 0o755); err != nil {
		return fmt.Errorf("mkdir archive root: %w", err)
	}

	entries, err := os.ReadDir(archiveRoot)
	if err != nil {
		return fmt.Errorf("read archive root: %w", err)
	}

	dirs := make([]string, 0)
	for _, entry := range entries {
		if entry.IsDir() {
			dirs = append(dirs, filepath.Join(archiveRoot, entry.Name()))
		}
	}

	sort.Strings(dirs)

	if !keepLastGood {
		for _, dir := range dirs {
			if err := os.RemoveAll(dir); err != nil {
				return fmt.Errorf("remove archive dir %s: %w", dir, err)
			}
		}
		return nil
	}

	if len(dirs) <= 1 {
		return nil
	}

	for _, dir := range dirs[:len(dirs)-1] {
		if err := os.RemoveAll(dir); err != nil {
			return fmt.Errorf("remove old archive dir %s: %w", dir, err)
		}
	}

	return nil
}

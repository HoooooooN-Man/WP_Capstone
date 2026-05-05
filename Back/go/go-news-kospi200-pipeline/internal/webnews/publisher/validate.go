package publisher

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
)

func LoadAndValidateStaging(stagingDir string, expectedDisplayDate string, expectedCategoryIDs []string) (model.FinalizeManifest, error) {
	manifestPath := filepath.Join(stagingDir, "manifest.json")

	b, err := os.ReadFile(manifestPath)
	if err != nil {
		return model.FinalizeManifest{}, fmt.Errorf("read manifest: %w", err)
	}

	var manifest model.FinalizeManifest
	if err := json.Unmarshal(b, &manifest); err != nil {
		return model.FinalizeManifest{}, fmt.Errorf("parse manifest: %w", err)
	}

	if strings.TrimSpace(manifest.DisplayDate) == "" {
		return model.FinalizeManifest{}, fmt.Errorf("manifest display_date is empty")
	}
	if manifest.DisplayDate != expectedDisplayDate {
		return model.FinalizeManifest{}, fmt.Errorf(
			"manifest display_date mismatch: got=%s want=%s",
			manifest.DisplayDate,
			expectedDisplayDate,
		)
	}

	if len(manifest.Categories) == 0 {
		return model.FinalizeManifest{}, fmt.Errorf("manifest categories is empty")
	}

	expected := make(map[string]struct{}, len(expectedCategoryIDs))
	for _, id := range expectedCategoryIDs {
		expected[strings.TrimSpace(id)] = struct{}{}
	}

	for _, categoryID := range manifest.Categories {
		categoryID = strings.TrimSpace(categoryID)
		if categoryID == "" {
			return model.FinalizeManifest{}, fmt.Errorf("manifest contains empty category id")
		}
		if _, ok := expected[categoryID]; !ok {
			return model.FinalizeManifest{}, fmt.Errorf("unexpected category in manifest: %s", categoryID)
		}

		path := filepath.Join(stagingDir, categoryID+".json")
		info, err := os.Stat(path)
		if err != nil {
			return model.FinalizeManifest{}, fmt.Errorf("missing category file %s: %w", path, err)
		}
		if info.IsDir() {
			return model.FinalizeManifest{}, fmt.Errorf("category path is directory, not file: %s", path)
		}
	}

	return manifest, nil
}

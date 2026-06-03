package fileout

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

func WriteJSON(path string, v any) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("mkdir parent dir: %w", err)
	}

	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal json: %w", err)
	}

	b = append(b, '\n')

	if err := os.WriteFile(path, b, 0o644); err != nil {
		return fmt.Errorf("write json file: %w", err)
	}

	return nil
}

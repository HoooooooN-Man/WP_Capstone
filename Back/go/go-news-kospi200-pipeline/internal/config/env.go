package config

import (
	"bufio"
	"log"
	"os"
	"strings"
	"sync"
)

var loadEnvOnce sync.Once

func loadDotEnv() {
	loadEnvOnce.Do(func() {
		candidates := []string{}
		if explicit := strings.TrimSpace(os.Getenv("APP_ENV_FILE")); explicit != "" {
			candidates = append(candidates, explicit)
		}
		candidates = append(candidates,
			".env",
			"configs/.env",
			"configs/.env.local",
		)

		for _, path := range candidates {
			if path == "" {
				continue
			}
			if err := loadEnvFile(path); err == nil {
				log.Printf("config: loaded env file %s", path)
				return
			}
		}
	})
}

func loadEnvFile(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if strings.HasPrefix(line, "export ") {
			line = strings.TrimSpace(strings.TrimPrefix(line, "export "))
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])
		value = strings.Trim(value, `"'`)
		if key == "" {
			continue
		}
		if _, exists := os.LookupEnv(key); exists {
			continue
		}
		_ = os.Setenv(key, value)
	}
	return scanner.Err()
}

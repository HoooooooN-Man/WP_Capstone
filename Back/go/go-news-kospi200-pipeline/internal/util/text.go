package util

import (
	"crypto/sha256"
	"encoding/hex"
	"regexp"
	"strings"
)

var (
	multiSpace = regexp.MustCompile(`\s+`)
	bracketTag = regexp.MustCompile(`^(\[[^\]]+\]|\([^\)]+\))\s*`)
	noisePunct = regexp.MustCompile(`[“”"'` + "`" + `…·,:;!?]+`)
)

func NormalizeTitle(s string) string {
	s = strings.TrimSpace(s)
	for {
		next := bracketTag.ReplaceAllString(s, "")
		if next == s {
			break
		}
		s = strings.TrimSpace(next)
	}
	s = noisePunct.ReplaceAllString(s, " ")
	s = strings.ToLower(strings.TrimSpace(s))
	s = multiSpace.ReplaceAllString(s, " ")
	return s
}

func SHA256Hex(s string) string {
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])
}

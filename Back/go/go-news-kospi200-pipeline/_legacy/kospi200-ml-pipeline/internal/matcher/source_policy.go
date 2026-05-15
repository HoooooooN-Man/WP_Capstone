package matcher

import (
    "encoding/json"
    "os"
    "regexp"
    "strings"
)

type SourcePolicy struct {
    DigestOnlySources             []string `json:"digest_only_sources"`
    MLBlockedSources              []string `json:"ml_blocked_sources"`
    MLBlockedTitlePatterns        []string `json:"ml_blocked_title_patterns"`
    MLBlockedQueryPatterns        []string `json:"ml_blocked_query_patterns"`
    LowQualitySources             []string `json:"low_quality_sources"`
    AggregatorSources             []string `json:"aggregator_sources"`
    NormalizeSourceContainsMatch  bool     `json:"normalize_source_contains_match"`
}

func DefaultSourcePolicy() SourcePolicy {
    return SourcePolicy{
        DigestOnlySources: []string{
            "네이트", "v.daum.net", "다음", "topstarnews.net", "톱스타뉴스", "주달",
        },
        MLBlockedSources: []string{
            "네이트", "v.daum.net", "다음", "topstarnews.net", "톱스타뉴스", "주달",
        },
        MLBlockedTitlePatterns: []string{
            "투자분석", "주가,", "장중", "[오늘의 증시일정]", "오늘의 증시일정", "증시일정",
        },
        MLBlockedQueryPatterns: []string{},
        LowQualitySources: []string{
            "topstarnews.net", "톱스타뉴스", "주달", "네이트",
        },
        AggregatorSources: []string{
            "네이트", "v.daum.net", "다음",
        },
        NormalizeSourceContainsMatch: true,
    }
}

func LoadSourcePolicy(path string) SourcePolicy {
    policy := DefaultSourcePolicy()
    if path == "" {
        return policy
    }
    b, err := os.ReadFile(path)
    if err != nil {
        return policy
    }
    _ = json.Unmarshal(b, &policy)
    return policy
}

func normalizeSourceName(s string) string {
    s = strings.TrimSpace(strings.ToLower(s))
    s = strings.ReplaceAll(s, "https://", "")
    s = strings.ReplaceAll(s, "http://", "")
    s = strings.ReplaceAll(s, "www.", "")
    s = strings.TrimSpace(s)
    return s
}

func containsAnyNormalizedSource(source string, values []string) bool {
    sourceNorm := normalizeSourceName(source)
    for _, v := range values {
        vNorm := normalizeSourceName(v)
        if vNorm == "" {
            continue
        }
        if sourceNorm == vNorm || strings.Contains(sourceNorm, vNorm) || strings.Contains(vNorm, sourceNorm) {
            return true
        }
    }
    return false
}

func containsAnyFold(s string, patterns []string) bool {
    s = strings.ToLower(strings.TrimSpace(s))
    for _, p := range patterns {
        p = strings.ToLower(strings.TrimSpace(p))
        if p == "" {
            continue
        }
        if strings.Contains(s, p) {
            return true
        }
    }
    return false
}

var reSpace = regexp.MustCompile(`\s+`)

func compactSpaces(s string) string {
    return strings.TrimSpace(reSpace.ReplaceAllString(s, " "))
}

func (p SourcePolicy) ClassifySource(sourceName string) string {
    if containsAnyNormalizedSource(sourceName, p.MLBlockedSources) {
        return "blocked"
    }
    if containsAnyNormalizedSource(sourceName, p.LowQualitySources) {
        return "low"
    }
    return "normal"
}

func (p SourcePolicy) ShouldUseForML(sourceName, query, title string, isMacro bool) (bool, string, string) {
    if isMacro {
        return false, "macro_query", p.ClassifySource(sourceName)
    }
    if containsAnyNormalizedSource(sourceName, p.MLBlockedSources) {
        return false, "blocked_source", p.ClassifySource(sourceName)
    }
    if containsAnyFold(title, p.MLBlockedTitlePatterns) {
        return false, "blocked_title_pattern", p.ClassifySource(sourceName)
    }
    if containsAnyFold(query, p.MLBlockedQueryPatterns) {
        return false, "blocked_query_pattern", p.ClassifySource(sourceName)
    }
    return true, "", p.ClassifySource(sourceName)
}

func (p SourcePolicy) ShouldUseForDigest(sourceName string) bool {
    return true
}

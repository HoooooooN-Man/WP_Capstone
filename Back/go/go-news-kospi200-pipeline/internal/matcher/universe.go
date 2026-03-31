package matcher

import (
    "encoding/json"
    "html"
    "os"
    "path/filepath"
    "regexp"
    "sort"
    "strings"
    "unicode"

    "github.com/example/go-news-kospi200-pipeline/internal/model"
)

type MatchRules struct {
    MinAliasLength                     int      `json:"min_alias_length"`
    PreferExactCompanyName             bool     `json:"prefer_exact_company_name"`
    PreferTickerMatch                  bool     `json:"prefer_ticker_match"`
    DisallowSubstringMatchForAmbiguous bool     `json:"disallow_substring_match_for_ambiguous_roots"`
    AllowExactCompanyNameOverride      bool     `json:"allow_exact_company_name_override"`
    AmbiguousRootTokens                []string `json:"ambiguous_root_tokens"`
    WeakASCIIAliases                   []string `json:"weak_ascii_aliases"`
    ASCIIExactTokenMatch               bool     `json:"ascii_exact_token_match"`
    StripHTMLFromSnippet               bool     `json:"strip_html_from_snippet"`
    StripURLsFromSnippet               bool     `json:"strip_urls_from_snippet"`
    MaxArticleAgeDays                  int      `json:"max_article_age_days"`
    MacroQueries                       []string `json:"macro_queries"`
    ExactTokenAliases                  []string `json:"exact_token_aliases"`
    RemoveSourceNameFromSnippet        bool     `json:"remove_source_name_from_snippet"`
}

type Universe struct {
    Companies []model.CompanyAlias `json:"companies"`
    Rules     MatchRules           `json:"-"`
}

var (
    reHTMLTags = regexp.MustCompile(`(?is)<[^>]+>`)
    reURLs     = regexp.MustCompile(`https?://\S+`)
)

func normalizeSpecialSeparators(s string) string {
    replacer := strings.NewReplacer(
        "ㆍ", " ",
        "·", " ",
        "•", " ",
        "∙", " ",
    )
    return compactSpaces(replacer.Replace(s))
}

func LoadUniverse(path string) (Universe, error) {
    b, err := os.ReadFile(path)
    if err != nil {
        return Universe{}, err
    }
    var u Universe
    if err := json.Unmarshal(b, &u); err != nil {
        return Universe{}, err
    }

    rulesPath := filepath.Join(filepath.Dir(path), "kospi200.match_rules.current.json")
    if rb, err := os.ReadFile(rulesPath); err == nil {
        var rules MatchRules
        if err := json.Unmarshal(rb, &rules); err == nil {
            u.Rules = rules
        }
    }
    if u.Rules.MinAliasLength == 0 {
        u.Rules.MinAliasLength = 2
    }
    if u.Rules.MaxArticleAgeDays == 0 {
        u.Rules.MaxArticleAgeDays = 30
    }
    if len(u.Rules.WeakASCIIAliases) == 0 {
        u.Rules.WeakASCIIAliases = []string{"SK", "LG", "KT", "GS", "HD", "DL", "LS", "CJ"}
    }
    if len(u.Rules.MacroQueries) == 0 {
        u.Rules.MacroQueries = []string{"금리", "환율", "코스피", "반도체"}
    }
    return u, nil
}

type MatchResult struct {
    CompanyName string
    Ticker      string
    MatchType   string
    MatchScore  float64
}

func (u Universe) MatchTitle(title string) []MatchResult {
    norm := normalizeMatchText(title, u.Rules)
    tokens := strings.Fields(norm)
    results := make([]MatchResult, 0)
    for _, c := range u.Companies {
        seen := map[string]struct{}{}
        candidates := append([]string{c.CompanyNameKO, c.CompanyNameEN, c.Ticker}, c.Aliases...)
        for _, alias := range candidates {
            alias = strings.TrimSpace(alias)
            if alias == "" {
                continue
            }
            aliasNorm := normalizeMatchText(alias, u.Rules)
            if aliasNorm == "" {
                continue
            }
            if isWeakAlias(aliasNorm, u.Rules) {
                continue
            }
            if utf8Len(aliasNorm) < u.Rules.MinAliasLength && !isNumeric(aliasNorm) {
                continue
            }
            if !hasAliasMatch(norm, tokens, aliasNorm, u.Rules) {
                continue
            }
            if containsNegativeAlias(norm, c.NegativeAliases, u.Rules) && inferMatchType(aliasNorm, c) == "alias" {
                continue
            }

            key := c.Ticker + ":" + aliasNorm
            if _, ok := seen[key]; ok {
                continue
            }
            seen[key] = struct{}{}
            results = append(results, MatchResult{
                CompanyName: c.CompanyNameKO,
                Ticker:      c.Ticker,
                MatchType:   inferMatchType(aliasNorm, c),
                MatchScore:  1.0,
            })
        }
    }
    sort.Slice(results, func(i, j int) bool { return results[i].Ticker < results[j].Ticker })
    return dedupResults(results)
}

func (u Universe) IsMacroQuery(q string) bool {
    q = strings.TrimSpace(strings.ToLower(q))
    for _, it := range u.Rules.MacroQueries {
        if q == strings.ToLower(strings.TrimSpace(it)) {
            return true
        }
    }
    return false
}

func normalizeMatchText(s string, rules MatchRules) string {
    s = html.UnescapeString(strings.TrimSpace(s))
    s = normalizeSpecialSeparators(s)
    if rules.StripURLsFromSnippet {
        s = reURLs.ReplaceAllString(s, " ")
    }
    if rules.StripHTMLFromSnippet {
        s = reHTMLTags.ReplaceAllString(s, " ")
    }

    var b strings.Builder
    lastSpace := false
    for _, r := range strings.ToLower(s) {
        switch {
        case unicode.IsLetter(r) || unicode.IsNumber(r):
            b.WriteRune(r)
            lastSpace = false
        default:
            if !lastSpace {
                b.WriteRune(' ')
                lastSpace = true
            }
        }
    }
    return strings.Join(strings.Fields(b.String()), " ")
}

func isWeakAlias(alias string, rules MatchRules) bool {
    upper := strings.ToUpper(strings.TrimSpace(alias))
    for _, it := range rules.WeakASCIIAliases {
        if upper == strings.ToUpper(strings.TrimSpace(it)) {
            return true
        }
    }
    return false
}

func hasAliasMatch(norm string, tokens []string, aliasNorm string, rules MatchRules) bool {
    if aliasNorm == "" {
        return false
    }
    if isExactTokenAlias(aliasNorm, rules) {
        return hasTokenSequence(tokens, strings.Fields(aliasNorm))
    }
    if isNumeric(aliasNorm) {
        return strings.Contains(norm, aliasNorm)
    }
    if containsHangul(aliasNorm) {
        return strings.Contains(norm, aliasNorm)
    }
    if rules.ASCIIExactTokenMatch {
        return hasTokenSequence(tokens, strings.Fields(aliasNorm))
    }
    return strings.Contains(norm, aliasNorm)
}

func isExactTokenAlias(alias string, rules MatchRules) bool {
    alias = strings.TrimSpace(strings.ToLower(alias))
    for _, it := range rules.ExactTokenAliases {
        if alias == strings.TrimSpace(strings.ToLower(it)) {
            return true
        }
    }
    return false
}

func containsNegativeAlias(norm string, negatives []string, rules MatchRules) bool {
    for _, n := range negatives {
        normNeg := normalizeMatchText(n, rules)
        if normNeg != "" && strings.Contains(norm, normNeg) {
            return true
        }
    }
    return false
}

func hasTokenSequence(tokens, aliasTokens []string) bool {
    if len(aliasTokens) == 0 || len(tokens) < len(aliasTokens) {
        return false
    }
    for i := 0; i <= len(tokens)-len(aliasTokens); i++ {
        ok := true
        for j := 0; j < len(aliasTokens); j++ {
            if tokens[i+j] != aliasTokens[j] {
                ok = false
                break
            }
        }
        if ok {
            return true
        }
    }
    return false
}

func containsHangul(s string) bool {
    for _, r := range s {
        if r >= 0xAC00 && r <= 0xD7A3 {
            return true
        }
    }
    return false
}

func isNumeric(s string) bool {
    for _, r := range s {
        if !unicode.IsDigit(r) {
            return false
        }
    }
    return s != ""
}

func utf8Len(s string) int {
    return len([]rune(s))
}

func inferMatchType(alias string, c model.CompanyAlias) string {
    switch alias {
    case strings.ToLower(c.Ticker):
        return "ticker"
    case strings.ToLower(c.CompanyNameKO):
        return "company_name_ko"
    case strings.ToLower(c.CompanyNameEN):
        return "company_name_en"
    default:
        return "alias"
    }
}

func dedupResults(in []MatchResult) []MatchResult {
    seen := map[string]struct{}{}
    out := make([]MatchResult, 0, len(in))
    for _, it := range in {
        key := it.Ticker + ":" + it.MatchType
        if _, ok := seen[key]; ok {
            continue
        }
        seen[key] = struct{}{}
        out = append(out, it)
    }
    return out
}

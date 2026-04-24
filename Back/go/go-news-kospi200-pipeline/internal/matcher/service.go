package matcher

import (
    "context"
    "fmt"
    "log"
    "strings"
    "time"

    "github.com/example/go-news-kospi200-pipeline/internal/config"
    "github.com/example/go-news-kospi200-pipeline/internal/model"
    "github.com/example/go-news-kospi200-pipeline/internal/redisx"
    "github.com/example/go-news-kospi200-pipeline/internal/util"
    "github.com/redis/go-redis/v9"
)

type Service struct {
    cfg          config.Config
    client       *redis.Client
    universe     Universe
    sourcePolicy SourcePolicy
}

func NewService(cfg config.Config, client *redis.Client, universe Universe, sourcePolicy SourcePolicy) *Service {
    return &Service{cfg: cfg, client: client, universe: universe, sourcePolicy: sourcePolicy}
}

func (s *Service) Run(ctx context.Context) error {
    if err := redisx.EnsureGroup(ctx, s.client, s.cfg.RawStream, s.cfg.RawGroup); err != nil {
        return err
    }
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }
        msgs, err := redisx.ReadGroup(ctx, s.client, s.cfg.RawGroup, s.cfg.RawConsumer, s.cfg.RawStream, s.cfg.PollBlock, 20)
        if err != nil {
            return err
        }
        if len(msgs) == 0 {
            continue
        }
        for _, msg := range msgs {
            raw, err := redisx.ParsePayload[model.RawNewsEvent](msg)
            if err != nil {
                log.Printf("matcher: parse error: %v", err)
                _ = redisx.Ack(ctx, s.client, s.cfg.RawStream, s.cfg.RawGroup, msg.ID)
                continue
            }
            normalized, ok := s.normalizeAndMatch(raw)
            if !ok {
                _ = redisx.Ack(ctx, s.client, s.cfg.RawStream, s.cfg.RawGroup, msg.ID)
                continue
            }
            if duplicated, err := s.isDuplicate(ctx, normalized); err != nil {
                return err
            } else if duplicated {
                _ = redisx.Ack(ctx, s.client, s.cfg.RawStream, s.cfg.RawGroup, msg.ID)
                continue
            }
            if _, err := redisx.AddJSON(ctx, s.client, s.cfg.NormalizedStream, normalized, 200000); err != nil {
                return err
            }
            if err := redisx.Ack(ctx, s.client, s.cfg.RawStream, s.cfg.RawGroup, msg.ID); err != nil {
                return err
            }
        }
    }
}

func (s *Service) normalizeAndMatch(raw model.RawNewsEvent) (model.NormalizedNewsEvent, bool) {
    maxAgeDays := s.universe.Rules.MaxArticleAgeDays
    if maxAgeDays <= 0 {
        maxAgeDays = 30
    }
    if raw.PublishedAt.Before(time.Now().AddDate(0, 0, -maxAgeDays)) {
        return model.NormalizedNewsEvent{}, false
    }

    normalizedTitle := normalizeSpecialSeparators(raw.Title)
    titleNorm := util.NormalizeTitle(normalizedTitle)
    snippetForMatching := normalizeSpecialSeparators(raw.Snippet)
    if s.universe.Rules.RemoveSourceNameFromSnippet {
        snippetForMatching = stripSourceNameFromSnippet(snippetForMatching, raw.SourceName)
    }
    matches := s.universe.MatchTitle(strings.TrimSpace(normalizedTitle + " " + snippetForMatching))
    if len(matches) == 0 {
        return model.NormalizedNewsEvent{}, false
    }

    mapped := make([]model.MatchedCompany, 0, len(matches))
    for _, m := range matches {
        mapped = append(mapped, model.MatchedCompany{
            Ticker:      m.Ticker,
            CompanyName: m.CompanyName,
            MatchType:   m.MatchType,
            MatchScore:  m.MatchScore,
        })
    }
    hashSeed := fmt.Sprintf("%s|%s|%s", titleNorm, raw.SourceName, raw.PublishedAt.UTC().Format("2006-01-02T15"))
    isMacroQuery := s.universe.IsMacroQuery(raw.Query)
    usedForML, mlReason, qualityTier := s.sourcePolicy.ShouldUseForML(raw.SourceName, raw.Query, raw.Title, isMacroQuery)
    usedForDigest := s.sourcePolicy.ShouldUseForDigest(raw.SourceName)
    if !usedForML && !usedForDigest {
        return model.NormalizedNewsEvent{}, false
    }

    return model.NormalizedNewsEvent{
        NewsID:            raw.NewsID,
        Provider:          raw.Provider,
        Query:             raw.Query,
        Title:             raw.Title,
        TitleNorm:         titleNorm,
        TitleHash:         util.SHA256Hex(hashSeed),
        SourceName:        raw.SourceName,
        GoogleURL:         raw.GoogleURL,
        ArticleURL:        raw.ArticleURL,
        Snippet:           raw.Snippet,
        PublishedAt:       raw.PublishedAt,
        FetchedAt:         raw.FetchedAt,
        Matched:           mapped,
        UsedForML:         usedForML,
        UsedForDigest:     usedForDigest,
        IsMacroQuery:      isMacroQuery,
        MLExclusionReason: mlReason,
        SourceQualityTier: qualityTier,
    }, true
}

func (s *Service) isDuplicate(ctx context.Context, item model.NormalizedNewsEvent) (bool, error) {
    key := fmt.Sprintf("%s:%s", s.cfg.DedupPrefix, time.Now().Format("20060102"))
    added, err := s.client.SAdd(ctx, key, item.TitleHash).Result()
    if err != nil {
        return false, err
    }
    _ = s.client.Expire(ctx, key, 72*time.Hour).Err()
    return added == 0, nil
}

func stripSourceNameFromSnippet(snippet, sourceName string) string {
    if sourceName == "" || snippet == "" {
        return normalizeSpecialSeparators(snippet)
    }
    snippet = normalizeSpecialSeparators(snippet)
    sourceName = normalizeSpecialSeparators(sourceName)
    replacer := strings.NewReplacer(
        sourceName, " ",
        strings.ToLower(sourceName), " ",
        strings.ToUpper(sourceName), " ",
    )
    return compactSpaces(replacer.Replace(snippet))
}

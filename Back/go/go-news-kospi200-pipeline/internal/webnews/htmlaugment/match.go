package htmlaugment

import (
	"strings"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/collector"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
)

type MatchResult struct {
	Card  *model.HTMLNewsCard
	Score int
}

func FindBestHTMLCard(raw model.RawNewsItem, cards []model.HTMLNewsCard) MatchResult {
	best := MatchResult{
		Card:  nil,
		Score: 0,
	}

	for i := range cards {
		score := scoreHTMLCardMatch(raw, cards[i])
		if score > best.Score {
			cardCopy := cards[i]
			best = MatchResult{
				Card:  &cardCopy,
				Score: score,
			}
		}
	}

	// 너무 애매한 매칭은 버린다.
	if best.Score < 70 {
		return MatchResult{}
	}

	return best
}

func scoreHTMLCardMatch(raw model.RawNewsItem, card model.HTMLNewsCard) int {
	rawTitle := normalizeTitleForMatch(raw.Title)
	cardTitle := normalizeTitleForMatch(card.Title)

	rawPublisher := normalizePublisherForMatch(raw.Publisher)
	cardPublisher := normalizePublisherForMatch(card.Publisher)

	score := 0

	switch {
	case rawTitle != "" && cardTitle != "" && rawTitle == cardTitle:
		score += 100
	case rawTitle != "" && cardTitle != "" && strings.Contains(rawTitle, cardTitle):
		score += 75
	case rawTitle != "" && cardTitle != "" && strings.Contains(cardTitle, rawTitle):
		score += 75
	default:
		score += tokenOverlapScore(rawTitle, cardTitle)
	}

	if rawPublisher != "" && cardPublisher != "" {
		switch {
		case rawPublisher == cardPublisher:
			score += 30
		case strings.Contains(rawPublisher, cardPublisher) || strings.Contains(cardPublisher, rawPublisher):
			score += 20
		}
	}

	if strings.TrimSpace(raw.GoogleNewsURL) != "" &&
		strings.TrimSpace(card.GoogleNewsURL) != "" &&
		strings.TrimSpace(raw.GoogleNewsURL) == strings.TrimSpace(card.GoogleNewsURL) {
		score += 25
	}

	if strings.TrimSpace(raw.Query) != "" &&
		strings.TrimSpace(card.Query) != "" &&
		strings.TrimSpace(raw.Query) == strings.TrimSpace(card.Query) {
		score += 10
	}

	if strings.TrimSpace(card.PossibleURL) != "" {
		score += 5
	}
	if strings.TrimSpace(card.ThumbnailURL) != "" {
		score += 3
	}

	return score
}

func normalizeTitleForMatch(s string) string {
	s = collector.NormalizeTitle(s)
	s = strings.ToLower(strings.TrimSpace(s))
	s = strings.NewReplacer(
		`"`, "",
		`'`, "",
		"[", " ",
		"]", " ",
		"(", " ",
		")", " ",
		"“", "",
		"”", "",
		"‘", "",
		"’", "",
		":", " ",
		",", " ",
		"...", " ",
	).Replace(s)
	s = strings.Join(strings.Fields(s), " ")
	return s
}

func normalizePublisherForMatch(s string) string {
	s = collector.CleanPublisher(s)
	s = strings.ToLower(strings.TrimSpace(s))
	s = strings.NewReplacer(
		"(주)", "",
		"뉴스", "",
		"신문", "",
		"닷컴", "",
	).Replace(s)
	s = strings.Join(strings.Fields(s), " ")
	return s
}

func tokenOverlapScore(a, b string) int {
	if a == "" || b == "" {
		return 0
	}

	setA := tokenSet(a)
	setB := tokenSet(b)

	if len(setA) == 0 || len(setB) == 0 {
		return 0
	}

	common := 0
	for token := range setA {
		if _, ok := setB[token]; ok {
			common++
		}
	}

	switch {
	case common >= 7:
		return 70
	case common == 6:
		return 60
	case common == 5:
		return 50
	case common == 4:
		return 40
	case common == 3:
		return 30
	case common == 2:
		return 20
	case common == 1:
		return 10
	default:
		return 0
	}
}

func tokenSet(s string) map[string]struct{} {
	fields := strings.Fields(strings.TrimSpace(s))
	out := make(map[string]struct{}, len(fields))
	for _, f := range fields {
		f = strings.TrimSpace(f)
		if f == "" {
			continue
		}
		out[f] = struct{}{}
	}
	return out
}

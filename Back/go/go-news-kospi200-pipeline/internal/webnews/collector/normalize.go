package collector

import (
	"html"
	"regexp"
	"strings"
)

var multiSpaceRE = regexp.MustCompile(`\s+`)

func NormalizeTitle(s string) string {
	s = html.UnescapeString(s)

	replacer := strings.NewReplacer(
		"ㆍ", " ",
		"·", " ",
		"•", " ",
		"｜", " ",
		"|", " ",
		"\t", " ",
		"\n", " ",
		"\r", " ",
	)

	s = replacer.Replace(s)
	s = multiSpaceRE.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

func CleanPublisher(s string) string {
	s = html.UnescapeString(strings.TrimSpace(s))
	s = strings.TrimSuffix(s, " -")
	s = strings.Trim(s, " -|\n\r\t")
	s = multiSpaceRE.ReplaceAllString(s, " ")
	return s
}

func SplitTitleAndPublisher(rawTitle, fallbackPublisher string) (string, string) {
	title := NormalizeTitle(rawTitle)
	publisher := CleanPublisher(fallbackPublisher)

	// Google News RSS에서는 제목 끝에 " - 매체명" 형태가 섞여 들어오는 경우가 있다.
	seps := []string{" - ", " | ", " — ", " – "}

	if publisher == "" {
		for _, sep := range seps {
			if strings.Count(title, sep) < 1 {
				continue
			}

			parts := strings.Split(title, sep)
			if len(parts) < 2 {
				continue
			}

			tail := CleanPublisher(parts[len(parts)-1])
			head := strings.TrimSpace(strings.Join(parts[:len(parts)-1], sep))

			if tail != "" && head != "" {
				title = NormalizeTitle(head)
				publisher = tail
				break
			}
		}
	}

	return title, publisher
}

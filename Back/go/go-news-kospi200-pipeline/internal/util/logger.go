package util

import (
	"context"
	"io"
	"log/slog"
	"os"
	"strings"
)

// SetupLogger 는 환경변수 기반으로 표준 라이브러리 log/slog 를 초기화한다.
//
//	LOG_LEVEL  : debug | info | warn | error  (default: info)
//	LOG_FORMAT : json | text                  (default: json)
//
// JSON 출력은 Loki/Promtail/Vector 등에서 별도 파싱 없이 바로 색인된다.
//
// 호출 예 (각 cmd/*/main.go 진입부):
//
//	util.SetupLogger("collector")
//	slog.Info("started", "query", q, "fetched", n)
func SetupLogger(service string) *slog.Logger {
	level := parseLevel(os.Getenv("LOG_LEVEL"))
	format := strings.ToLower(os.Getenv("LOG_FORMAT"))

	out := io.Writer(os.Stderr)

	var handler slog.Handler
	if format == "text" {
		handler = slog.NewTextHandler(out, &slog.HandlerOptions{
			Level:     level,
			AddSource: false,
		})
	} else {
		handler = slog.NewJSONHandler(out, &slog.HandlerOptions{
			Level:     level,
			AddSource: false,
		})
	}

	logger := slog.New(handler).With(
		"service", service,
		"env", strOr(os.Getenv("APP_ENV"), "dev"),
	)
	slog.SetDefault(logger)
	return logger
}

func parseLevel(s string) slog.Level {
	switch strings.ToLower(s) {
	case "debug":
		return slog.LevelDebug
	case "warn", "warning":
		return slog.LevelWarn
	case "error", "err":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}

func strOr(v, def string) string {
	if v == "" {
		return def
	}
	return v
}

// LogErr 은 컨텍스트와 에러 메시지를 함께 구조화 로그로 남기는 헬퍼.
// 에러가 nil 이면 noop.
func LogErr(ctx context.Context, msg string, err error, attrs ...any) {
	if err == nil {
		return
	}
	slog.LogAttrs(ctx, slog.LevelError, msg, append(
		[]slog.Attr{slog.String("error", err.Error())},
		toAttrs(attrs)...,
	)...)
}

func toAttrs(kvs []any) []slog.Attr {
	out := make([]slog.Attr, 0, len(kvs)/2)
	for i := 0; i+1 < len(kvs); i += 2 {
		key, _ := kvs[i].(string)
		out = append(out, slog.Any(key, kvs[i+1]))
	}
	return out
}

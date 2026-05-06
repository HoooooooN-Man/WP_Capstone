package timewindow

import (
	"fmt"
	"time"
)

func WindowForDisplayDate(displayDate string, loc *time.Location, openHour, openMinute int) (time.Time, time.Time, error) {
	day, err := time.ParseInLocation("2006-01-02", displayDate, loc)
	if err != nil {
		return time.Time{}, time.Time{}, fmt.Errorf("parse display_date: %w", err)
	}

	displayOpen := time.Date(
		day.Year(),
		day.Month(),
		day.Day(),
		openHour,
		openMinute,
		0,
		0,
		loc,
	)

	windowStart := displayOpen.AddDate(0, 0, -1)
	windowEnd := displayOpen.Add(-time.Second)

	return windowStart, windowEnd, nil
}

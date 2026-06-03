package timewindow

import "time"

func Resolve(now time.Time, loc *time.Location, openHour, openMinute int) (displayDate string, windowStart, windowEnd time.Time) {
	localNow := now.In(loc)

	openToday := time.Date(
		localNow.Year(),
		localNow.Month(),
		localNow.Day(),
		openHour,
		openMinute,
		0,
		0,
		loc,
	)

	var displayOpen time.Time
	if localNow.Before(openToday) {
		displayOpen = openToday
	} else {
		displayOpen = openToday.AddDate(0, 0, 1)
	}

	windowStart = displayOpen.AddDate(0, 0, -1)
	windowEnd = displayOpen.Add(-time.Second)

	return displayOpen.Format("2006-01-02"), windowStart, windowEnd
}

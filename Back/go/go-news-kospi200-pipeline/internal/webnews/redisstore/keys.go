package redisstore

import "fmt"

func StreamCollectJobs(prefix string) string {
	return fmt.Sprintf("%s:collect_jobs", prefix)
}

func StreamRawItems(prefix string) string {
	return fmt.Sprintf("%s:raw_items", prefix)
}

func StreamPublishEvents(prefix string) string {
	return fmt.Sprintf("%s:publish_events", prefix)
}

func DisplayDatePrefix(prefix, displayDate string) string {
	return fmt.Sprintf("%s:%s", prefix, displayDate)
}

func ItemKey(prefix, displayDate, itemID string) string {
	return fmt.Sprintf("%s:%s:item:%s", prefix, displayDate, itemID)
}

func RankKey(prefix, displayDate, category string) string {
	return fmt.Sprintf("%s:%s:rank:%s", prefix, displayDate, category)
}

func SeenKey(prefix, displayDate, category string) string {
	return fmt.Sprintf("%s:%s:seen:%s", prefix, displayDate, category)
}

func LockFinalizeKey(prefix, displayDate string) string {
	return fmt.Sprintf("%s:%s:lock:finalize", prefix, displayDate)
}

func LockPublishKey(prefix, displayDate string) string {
	return fmt.Sprintf("%s:%s:lock:publish", prefix, displayDate)
}

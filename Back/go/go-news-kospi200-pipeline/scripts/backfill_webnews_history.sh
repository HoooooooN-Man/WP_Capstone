#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export APP_ENV_FILE="${APP_ENV_FILE:-configs/webnews.env}"

START_DATE="${1:-2026-05-01}"
END_DATE="${2:-2026-05-16}"

export HISTORY_ROOT="${WEBNEWS_HISTORY_DIR:-data/webnews/history}"
export EXPORT_ROOT="${WEBNEWS_HISTORY_EXPORT_DIR:-exports/webnews-history}"

mkdir -p "$HISTORY_ROOT"
mkdir -p "$EXPORT_ROOT"

echo "============================================================"
echo "[START] webnews history backfill"
echo "============================================================"
echo "[INFO] root_dir=$ROOT_DIR"
echo "[INFO] app_env_file=$APP_ENV_FILE"
echo "[INFO] start_date=$START_DATE"
echo "[INFO] end_date=$END_DATE"
echo "[INFO] history_root=$HISTORY_ROOT"
echo "[INFO] export_root=$EXPORT_ROOT"
echo

current="$START_DATE"

while true; do
  echo "------------------------------------------------------------"
  echo "[BACKFILL] display_date=$current"
  echo "------------------------------------------------------------"

  APP_ENV_FILE="$APP_ENV_FILE" bash scripts/run_webnews_daily_batch.sh "$current"

  src_dir="$ROOT_DIR/data/webnews/current"
  dest_dir="$ROOT_DIR/$HISTORY_ROOT/$current"
  tmp_dir="$dest_dir.tmp"

  if [[ ! -f "$src_dir/manifest.json" ]]; then
    echo "[ERROR] manifest.json not found after batch: $src_dir/manifest.json" >&2
    exit 1
  fi

  rm -rf "$tmp_dir"
  mkdir -p "$tmp_dir"

  cp -a "$src_dir"/. "$tmp_dir"/

  rm -rf "$dest_dir"
  mv "$tmp_dir" "$dest_dir"

  echo "[OK] saved history: $dest_dir"
  echo

  if [[ "$current" == "$END_DATE" ]]; then
    break
  fi

  current="$(date -I -d "$current + 1 day")"
done

echo "------------------------------------------------------------"
echo "[EXPORT] build JSONL and summary"
echo "------------------------------------------------------------"

export START_DATE
export END_DATE

python3 - <<'PY'
import json
import os
from pathlib import Path

history_root = Path(os.environ["HISTORY_ROOT"])
export_root = Path(os.environ["EXPORT_ROOT"])
start_date = os.environ["START_DATE"]
end_date = os.environ["END_DATE"]

jsonl_path = export_root / f"items-{start_date}_{end_date}.jsonl"
summary_path = export_root / f"summary-{start_date}_{end_date}.json"

category_files = [
    "korea.json",
    "world.json",
    "business.json",
    "science_tech.json",
    "policy_finance.json",
    "industry_ai.json",
]

summary = {
    "start_date": start_date,
    "end_date": end_date,
    "date_count": 0,
    "total_item_count": 0,
    "dates": {},
}

with jsonl_path.open("w", encoding="utf-8") as out:
    for date_dir in sorted(history_root.iterdir()):
        if not date_dir.is_dir():
            continue

        display_date = date_dir.name
        if display_date < start_date or display_date > end_date:
            continue

        manifest_path = date_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        date_summary = {
            "display_date": display_date,
            "window_start": manifest.get("window_start", ""),
            "window_end": manifest.get("window_end", ""),
            "categories": {},
            "item_count": 0,
        }

        for filename in category_files:
            path = date_dir / filename
            if not path.exists():
                continue

            data = json.loads(path.read_text(encoding="utf-8"))
            category_id = data.get("category_id", filename.replace(".json", ""))
            category_label = data.get("category_label", "")
            items = data.get("items", [])

            date_summary["categories"][category_id] = len(items)
            date_summary["item_count"] += len(items)

            for item in items:
                record = {
                    "display_date": display_date,
                    "window_start": data.get("window_start", manifest.get("window_start", "")),
                    "window_end": data.get("window_end", manifest.get("window_end", "")),
                    "category_id": category_id,
                    "category_label": category_label,
                    "rank": item.get("rank"),
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "publisher": item.get("publisher"),
                    "google_news_url": item.get("google_news_url"),
                    "published_at": item.get("published_at"),
                    "collected_at": item.get("collected_at"),
                    "score": item.get("score"),
                    "seen_count": item.get("seen_count"),
                    "best_rank": item.get("best_rank"),
                    "latest_rank": item.get("latest_rank"),
                    "source": item.get("source"),
                    "query": item.get("query"),
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")

        summary["date_count"] += 1
        summary["total_item_count"] += date_summary["item_count"]
        summary["dates"][display_date] = date_summary

summary_path.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"[OK] jsonl={jsonl_path}")
print(f"[OK] summary={summary_path}")
print(f"[OK] dates={summary['date_count']} total_items={summary['total_item_count']}")
PY

echo
echo "============================================================"
echo "[DONE] webnews history backfill"
echo "============================================================"
echo "[INFO] history_root=$HISTORY_ROOT"
echo "[INFO] jsonl=$EXPORT_ROOT/items-${START_DATE}_${END_DATE}.jsonl"
echo "[INFO] summary=$EXPORT_ROOT/summary-${START_DATE}_${END_DATE}.json"
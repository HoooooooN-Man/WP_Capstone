import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import redis
import requests
from dotenv import load_dotenv
from analyzer import SentimentAnalyzer  # 분석기 클래스 임포트

# .env 파일 로드
load_dotenv()

# --- 환경 설정 ---
REDIS_CONF = {
    "host": os.getenv("REDIS_HOST"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "password": os.getenv("REDIS_PASSWORD"),
    "decode_responses": os.getenv("REDIS_DECODE_RESPONSES", "True").lower() == "true",
    "socket_timeout": int(os.getenv("REDIS_SOCKET_TIMEOUT", 60)),
    "socket_connect_timeout": int(os.getenv("REDIS_CONNECT_TIMEOUT", 10)),
    "retry_on_timeout": os.getenv("REDIS_RETRY_ON_TIMEOUT", "True").lower() == "true",
}

DB_SERVER_URL = os.getenv("DB_SERVER_URL", "").strip()
POLL_INTERVAL_SECONDS = int(os.getenv("WEBNEWS_POLL_INTERVAL_SECONDS", 30))
DB_REQUEST_TIMEOUT = int(os.getenv("DB_REQUEST_TIMEOUT", 30))
WEBNEWS_TOP_N_DEFAULT = int(os.getenv("WEBNEWS_TOP_N_DEFAULT", 10))
STATE_FILE = Path(os.getenv("WEBNEWS_STATE_FILE", "./.webnews_ingestion_state.json"))
EXPORT_DIR = os.getenv("WEBNEWS_EXPORT_DIR", "").strip()

DEFAULT_CATEGORIES = [
    "korea", "world", "business", "science_tech", "policy_finance", "industry_ai",
]

# --- 유틸리티 함수 ---
def get_redis_client() -> redis.Redis:
    return redis.Redis(**REDIS_CONF)

def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None or value == "": return default
    try: return int(value)
    except: return default

def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or value == "": return default
    try: return float(value)
    except: return default

def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists(): return {}
    try: return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except: return {}

def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_categories_from_manifest(manifest_hash: Dict[str, str]) -> List[str]:
    manifest_json = manifest_hash.get("manifest_json", "")
    if manifest_json:
        try:
            parsed = json.loads(manifest_json)
            categories = parsed.get("categories", [])
            if isinstance(categories, list) and categories:
                return [str(x).strip() for x in categories if str(x).strip()]
        except: pass
    return []

def scan_categories_from_redis(rd: redis.Redis, display_date: str) -> List[str]:
    pattern = f"webnews:{display_date}:rank:*"
    found = []
    for key in rd.scan_iter(match=pattern):
        parts = key.split(":")
        if len(parts) >= 4:
            category_id = parts[-1].strip()
            if category_id and category_id not in found:
                found.append(category_id)
    return found

def get_categories(rd: redis.Redis, manifest_hash: Dict[str, str], display_date: str) -> List[str]:
    categories = parse_categories_from_manifest(manifest_hash)
    if categories: return categories
    categories = scan_categories_from_redis(rd, display_date)
    return categories if categories else DEFAULT_CATEGORIES

# --- 분석 및 정규화 로직 ---
def normalize_and_analyze_item(item_hash: Dict[str, str], rank: int, rank_score: float, analyzer: SentimentAnalyzer) -> Dict[str, Any]:
    item = dict(item_hash)
    
    # 타입 변환
    for key in ["seen_count", "best_rank", "latest_rank"]:
        item[key] = safe_int(item.get(key), 0)
    item["score"] = safe_float(item.get("score"), 0.0)
    
    item["rank"] = rank
    item["rank_score"] = float(rank_score)

    # FinBERT 감성 분석 추가
    title = item.get("title", "")
    if title:
        item["sentiment"] = analyzer.analyze(title)
    
    return item

def load_current_webnews_from_redis(rd: redis.Redis, analyzer: SentimentAnalyzer) -> Dict[str, Any]:
    manifest_key = "webnews:current:manifest"
    manifest_hash = rd.hgetall(manifest_key)

    if not manifest_hash:
        raise RuntimeError("webnews:current:manifest not found in Redis")

    display_date = manifest_hash.get("display_date", "").strip()
    if not display_date:
        raise RuntimeError("display_date missing in manifest")

    categories = get_categories(rd, manifest_hash, display_date)
    top_n = safe_int(manifest_hash.get("top_n"), WEBNEWS_TOP_N_DEFAULT) or WEBNEWS_TOP_N_DEFAULT

    payload: Dict[str, Any] = {
        "source": "webnews_redis_current_v2",
        "display_date": display_date,
        "window_start": manifest_hash.get("window_start", ""),
        "window_end": manifest_hash.get("window_end", ""),
        "generated_at": manifest_hash.get("generated_at", ""),
        "top_n": top_n,
        "categories": [],
    }

    total_item_count = 0
    for category_id in categories:
        rank_key = f"webnews:{display_date}:rank:{category_id}"
        ranked = rd.zrevrange(rank_key, 0, top_n - 1, withscores=True)

        items = []
        for idx, (item_id, rank_score) in enumerate(ranked, start=1):
            item_key = f"webnews:{display_date}:item:{item_id}"
            item_hash = rd.hgetall(item_key)
            if not item_hash: continue

            # 정규화와 동시에 분석 수행
            normalized = normalize_and_analyze_item(item_hash, idx, rank_score, analyzer)
            items.append(normalized)

        payload["categories"].append({
            "category_id": category_id,
            "item_count": len(items),
            "items": items,
        })
        total_item_count += len(items)

    payload["category_count"] = len(payload["categories"])
    payload["total_item_count"] = total_item_count
    return payload

# --- 전송 로직 ---
def send_to_db(payload: Dict[str, Any]) -> None:
    if not DB_SERVER_URL:
        print("[WARN] DB_SERVER_URL is empty. Skip DB POST.")
        return

    response = requests.post(DB_SERVER_URL, json=payload, timeout=DB_REQUEST_TIMEOUT)
    response.raise_for_status()
    print(f"[OK] DB response: {response.status_code}")

def build_state_key(payload: Dict[str, Any]) -> str:
    return f"{payload.get('display_date')}|{payload.get('generated_at')}|{payload.get('total_item_count')}"

# --- 메인 루프 ---
def process_current_webnews_loop() -> None:
    # 1. FinBERT 모델 로딩 (시간 소요)
    print("[*] FinBERT 모델 로딩 중... 잠시만 기다려 주세요.")
    analyzer = SentimentAnalyzer()
    print(f"[+] 모델 로딩 완료! (Device: {analyzer.device})")

    rd = get_redis_client()
    state = load_state()

    print(f"[*] 분석 워커 가동! (Interval: {POLL_INTERVAL_SECONDS}s)")

    while True:
        try:
            if not rd.ping():
                raise RuntimeError("Redis connection lost")

            payload = load_current_webnews_from_redis(rd, analyzer)
            state_key = build_state_key(payload)

            # 중복 처리 방지
            if state.get("last_sent_key") == state_key:
                print(f"[{time.strftime('%H:%M:%S')}] 변경 사항 없음. 대기 중...")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            print(f"[{time.strftime('%H:%M:%S')}] 새 데이터 발견! 분석 및 전송 중... ({payload.get('total_item_count')} items)")

            # DB 전송
            send_to_db(payload)

            # 상태 업데이트 및 저장
            state.update({
                "last_sent_key": state_key,
                "last_display_date": payload.get("display_date"),
                "last_sent_at": time.strftime("%Y-%m-%dT%H:%M:%S")
            })
            save_state(state)
            print("[OK] 처리 및 상태 저장 완료")

        except Exception as e:
            print(f"[ERR] 작업 실패: {e}")
            time.sleep(5)  # 에러 발생 시 잠시 대기

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    process_current_webnews_loop()
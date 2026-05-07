"""
services/_core.py
=================
공유 인프라 — Redis 캐시, DuckDB 연결, 모델 버전 해석.

`services/*_svc.py` 와 `services/data.py` 는 모두 이 모듈에서 헬퍼를 가져와 쓴다.
연결·캐시 정책을 한 곳에서 관리하기 위해 분리됨 (services/data.py 1200+ 라인 분해 첫 단계).
"""

from __future__ import annotations

import hashlib
import json
import threading
import time as _time
from typing import Any, Callable

import duckdb

try:
    import redis as _redis_lib
    _REDIS_OK = True
except ImportError:
    _REDIS_OK = False

from ..core.config import (
    DUCKDB_PATH,
    NEWS_DUCKDB_PATH,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    REDIS_CACHE_TTL,
)


# ── Redis 연결 (싱글턴, 실패 허용) ───────────────────────────────────────────

_redis_client: Any = None
_redis_last_fail: float = 0.0
_REDIS_RETRY_INTERVAL = 30.0  # 실패 후 30초간 재시도 안 함


def get_redis():
    """Redis 클라이언트 (실패 시 None 반환, 30초간 재시도 억제)."""
    global _redis_client, _redis_last_fail
    if not _REDIS_OK:
        return None
    if _redis_client is not None:
        return _redis_client
    if _time.time() - _redis_last_fail < _REDIS_RETRY_INTERVAL:
        return None
    try:
        _redis_client = _redis_lib.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        _redis_client.ping()
    except Exception:
        _redis_client = None
        _redis_last_fail = _time.time()
    return _redis_client


def cache_key(fn_name: str, **kwargs) -> str:
    raw = json.dumps({"fn": fn_name, **kwargs}, sort_keys=True, default=str)
    return "ml_api:" + hashlib.md5(raw.encode()).hexdigest()


# 빈 배열 Redis 히트는 과거(DB 비어 있음·버전 불일치) 캐시가 오래 남아 404 를 유발할 수 있어 재조회함.
_REDIS_BYPASS_EMPTY_LIST = frozenset({"recommendations", "sector_summary"})


def cached(fn_name: str, fetch_fn: Callable[[], Any], ttl: int = REDIS_CACHE_TTL, **kwargs):
    """Redis 캐시 래퍼 — 직렬화는 JSON, 실패 시 캐시 없이 fetch_fn 직접 호출."""
    r = get_redis()
    key = cache_key(fn_name, **kwargs)
    if r:
        try:
            hit = r.get(key)
            if hit:
                parsed = json.loads(hit)
                if parsed == [] and fn_name in _REDIS_BYPASS_EMPTY_LIST:
                    try:
                        r.delete(key)
                    except Exception:
                        pass
                else:
                    return parsed
        except Exception:
            pass

    result = fetch_fn()

    if r:
        try:
            # 빈 리스트는 TTL 동안 버전/데이터가 바뀌어도 갱신되지 않는 문제를 막기 위해 저장하지 않음.
            if result != []:
                r.setex(key, ttl, json.dumps(result, default=str))
        except Exception:
            pass
    return result


# ── DuckDB 헬퍼 ─────────────────────────────────────────────────────────────

_duckdb_con: duckdb.DuckDBPyConnection | None = None
_duckdb_lock = threading.Lock()
_news_con_obj: duckdb.DuckDBPyConnection | None = None
_news_con_lock = threading.Lock()


def init_duckdb() -> None:
    """앱 시작 시(lifespan) 한 번만 호출 — 연결 + 워밍업으로 첫 요청 지연 제거."""
    global _duckdb_con
    with _duckdb_lock:
        if _duckdb_con is None:
            _duckdb_con = duckdb.connect(str(DUCKDB_PATH), read_only=True)

    con = _duckdb_con
    # 컬럼 스토리지 워밍업 (OS 파일 캐시 확보)
    con.execute("SELECT * FROM finance LIMIT 500").fetchdf()
    con.execute("SELECT * FROM scores  LIMIT 500").fetchdf()
    con.execute("SELECT * FROM prices  LIMIT 500").fetchdf()

    # 자주 쓰이는 집계 사전 실행 (HomeView 첫 진입 지연 해소)
    try:
        latest_ver_row = con.execute(
            "SELECT model_version FROM scores ORDER BY inserted_at DESC LIMIT 1"
        ).fetchone()
        if latest_ver_row:
            ver = latest_ver_row[0]
            latest_date_row = con.execute(
                "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?", [ver]
            ).fetchone()
            latest_date = latest_date_row[0] if latest_date_row else None
            if latest_date:
                con.execute(
                    """SELECT COUNT(*),
                              SUM(CASE WHEN tier='A' THEN 1 ELSE 0 END)
                       FROM scores
                       WHERE model_version=? AND CAST(date AS VARCHAR)=?""",
                    [ver, latest_date],
                ).fetchone()
                con.execute(
                    """SELECT sector, COUNT(*), AVG(score)
                       FROM scores
                       WHERE model_version=? AND CAST(date AS VARCHAR)=?
                       GROUP BY sector""",
                    [ver, latest_date],
                ).fetchdf()
                con.execute(
                    """SELECT * FROM scores
                       WHERE model_version=? AND CAST(date AS VARCHAR)=?
                       ORDER BY score DESC LIMIT 50""",
                    [ver, latest_date],
                ).fetchdf()
    except Exception:
        pass  # 워밍업 실패는 무시


def con() -> duckdb.DuckDBPyConnection:
    """읽기 전용 DuckDB 싱글턴 연결 (시장/스코어/재무)."""
    global _duckdb_con
    if _duckdb_con is None:
        with _duckdb_lock:
            if _duckdb_con is None:
                _duckdb_con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    return _duckdb_con


def news_con() -> duckdb.DuckDBPyConnection | None:
    """뉴스 전용 DuckDB read-only. 파일 미존재 시 None."""
    global _news_con_obj
    if _news_con_obj is not None:
        return _news_con_obj
    with _news_con_lock:
        if _news_con_obj is not None:
            return _news_con_obj
        if not NEWS_DUCKDB_PATH.exists():
            return None
        try:
            _news_con_obj = duckdb.connect(str(NEWS_DUCKDB_PATH), read_only=True)
        except Exception as e:
            print(f"[WARN] news DuckDB 연결 실패: {e}")
            return None
    return _news_con_obj


def resolve_version(model_version: str) -> str:
    """'latest' → 실제 버전 문자열.

    **차기 사이클 종료 시점 박제** — latest 의 자동 전환 동작:
      scores 테이블의 inserted_at 가장 최신 레코드 → 그 model_version.
      *새 모델을 precompute_scores 로 적재하면 latest 가 자동으로 그 모델로 전환됨.*
      예: v9 운영 중 v11a_prime 적재 → 다음 추천 호출부터 latest=v11a_prime.

    이게 *의도된 동작* (최신 모델로 자동 운영) 이지만 명시 결정 박제 없이 변경되므로:
      - W7B AB_SPLIT 으로 단계적 전환 권장 (canary 10% → 50/50 → 100%).
      - 차차기 사이클에서 트래픽 늘면 `DEFAULT_MODEL_VERSION` 환경변수 도입 검토.
        그 후 latest 는 명시적 default 의 alias 가 되도록.

    rollback: `DELETE FROM scores WHERE model_version='<new>'` 또는
    inserted_at 을 과거로 갱신해 이전 버전이 latest 되도록.
    """
    mv = (model_version or "").strip()
    if mv and mv.lower() != "latest":
        return mv
    # inserted_at 미기입(NULL) 레코드만 있어도 동작하도록 이중 폴백
    row = con().execute(
        """
        SELECT model_version FROM scores
        WHERE inserted_at IS NOT NULL
        ORDER BY inserted_at DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        row = con().execute(
            """
            SELECT model_version
            FROM scores
            GROUP BY 1
            ORDER BY MAX(CAST(date AS VARCHAR)) DESC NULLS LAST
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        raise RuntimeError(
            "scores 테이블이 비어 있습니다. precompute_scores.py 를 먼저 실행하세요."
        )
    return row[0]


def get_latest_date(model_version: str) -> str | None:
    """scores 테이블의 가장 최신 거래일 (YYYY-MM-DD 문자열).

    리팩토링 전 7곳에서 인라인으로 반복되던 쿼리를 단일 함수로 통합 (캡스톤 정리).
    호출자는 *resolved* model_version 을 넘겨야 한다 ('latest' 직접 사용 금지).
    """
    row = con().execute(
        "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?",
        [model_version],
    ).fetchone()
    return row[0] if row else None


def get_available_dates(model_version: str = "latest") -> list[str]:
    """scores 테이블의 날짜 목록(오름차순)."""
    ver = resolve_version(model_version)

    def fetch():
        rows = con().execute(
            """SELECT DISTINCT CAST(date AS VARCHAR) AS d
               FROM scores WHERE model_version = ?
               ORDER BY 1 ASC""",
            [ver],
        ).fetchall()
        return [r[0] for r in rows]

    return cached("available_dates", fetch, ttl=300, model_version=ver)


def get_available_versions() -> list[str]:
    """등록된 모든 model_version (최신 순)."""
    def fetch():
        rows = con().execute(
            """SELECT model_version, MAX(inserted_at) AS latest
               FROM scores GROUP BY 1 ORDER BY 2 DESC"""
        ).fetchall()
        return [r[0] for r in rows]

    return cached("available_versions", fetch, ttl=300)

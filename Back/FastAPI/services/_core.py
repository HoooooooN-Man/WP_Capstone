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
import os
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
#
# DuckDB 단일 Connection 객체는 스레드 동시 사용에 안전하지 않다. FastAPI 는
# 동기 핸들러를 스레드풀에서 실행하므로(종목 상세는 7+ 쿼리를 병렬 발사),
# 하나의 싱글턴 커넥션을 공유하면 동시 .execute() 가 서로 깨져 빈 결과·오류가
# 난다("scores 비어있음" 503 등). → 스레드별 read-only 커넥션을 둔다
# (read-only 는 동일 파일 다중 연결 허용).

_duckdb_base: duckdb.DuckDBPyConnection | None = None   # 워밍업·폴백용 베이스 핸들
_duckdb_lock = threading.Lock()
_duckdb_tls = threading.local()
_news_con_obj: duckdb.DuckDBPyConnection | None = None
_news_con_lock = threading.Lock()


def init_duckdb() -> None:
    """앱 시작 시(lifespan) 한 번만 호출 — 연결 + 워밍업으로 첫 요청 지연 제거."""
    global _duckdb_base
    with _duckdb_lock:
        if _duckdb_base is None:
            _duckdb_base = duckdb.connect(str(DUCKDB_PATH), read_only=True)

    con = _duckdb_base
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
    """읽기 전용 DuckDB 연결 — 스레드별 독립 커넥션.

    동시 요청이 같은 커넥션을 공유하면 .execute() 가 깨지므로 thread-local 로
    분리한다. read-only 라 동일 파일 다중 연결이 안전하다 (스레드당 1개 생성).
    """
    c = getattr(_duckdb_tls, "conn", None)
    if c is None:
        c = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        _duckdb_tls.conn = c
    return c


def news_con() -> duckdb.DuckDBPyConnection | None:
    """뉴스 전용 DuckDB read-only.

    NEWS_DUCKDB_PATH 파일이 존재하면 그것을 사용하고,
    없으면 메인 DB(DUCKDB_PATH=market_data.duckdb)로 폴백한다 —
    news_normalized/news_company_map/news_rankings 테이블이 메인 DB 에 적재돼 있음.
    """
    global _news_con_obj
    if _news_con_obj is not None:
        return _news_con_obj
    with _news_con_lock:
        if _news_con_obj is not None:
            return _news_con_obj
        # 1순위: 전용 뉴스 DB 파일
        if NEWS_DUCKDB_PATH.exists():
            try:
                _news_con_obj = duckdb.connect(str(NEWS_DUCKDB_PATH), read_only=True)
                return _news_con_obj
            except Exception as e:
                print(f"[WARN] news DuckDB 연결 실패: {e}")
        # 2순위: 메인 DB 폴백 (news_* 테이블이 존재하는지 확인)
        try:
            main = con()
            tbls = {r[0] for r in main.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()}
            if "news_normalized" in tbls:
                _news_con_obj = main
                return _news_con_obj
        except Exception as e:
            print(f"[WARN] news 메인 DB 폴백 실패: {e}")
        return None


DEFAULT_MODEL_VERSION_ENV = "DEFAULT_MODEL_VERSION"


def _model_version_exists(version: str) -> bool:
    """scores 테이블에 해당 model_version 행이 있는지 빠른 EXISTS 체크."""
    try:
        row = con().execute(
            "SELECT 1 FROM scores WHERE model_version=? LIMIT 1", [version],
        ).fetchone()
    except Exception:
        return False
    return row is not None


def resolve_version(model_version: str) -> str:
    """'latest' → 실제 버전 문자열.

    **결정 흐름** (차차기 W1 — DEFAULT_MODEL_VERSION 명시화):

    1. 호출자가 명시 버전 (예: "v9", "v11a_prime") 을 넘기면 그대로.
    2. "latest" / 빈 값 / None 인 경우:
       a. `DEFAULT_MODEL_VERSION` env var 가 설정돼있고 그 값이 scores 테이블에
          존재하면 → env var 값. *명시적 default*.
       b. env var 미설정 또는 그 값이 scores 에 부재 → inserted_at 가장 최신
          (차기 사이클 동작 보존, fallback).
       c. scores 비어있음 → RuntimeError.

    rollback (운영 default 변경 회피):
      - 즉시: `unset DEFAULT_MODEL_VERSION` 또는 이전 버전으로 변경.
      - 항구: scores 테이블에서 새 모델 DELETE 또는 inserted_at 과거화.

    캐시: resolve_version() 결과가 캐시 키 (cache_key model_version 인자) 의 일부.
    명시 default 가 바뀌면 새 키 → 기존 캐시는 자연 만료 (별도 invalidate 불필요).
    """
    mv = (model_version or "").strip()
    if mv and mv.lower() != "latest":
        return mv

    # 차차기 W1 — env var 명시 default 우선.
    env_default = (os.getenv(DEFAULT_MODEL_VERSION_ENV) or "").strip()
    if env_default and _model_version_exists(env_default):
        return env_default
    # env var 부재 또는 부정합 → fallback (차기 동작 보존).

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

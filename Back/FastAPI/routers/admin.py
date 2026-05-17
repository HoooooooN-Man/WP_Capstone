"""
routers/admin.py
================
운영 진단 엔드포인트 — M#35 cron_runs 텔레메트리 조회.

  GET /api/v1/admin/cron-runs        최근 N건의 cron/배치 실행 상태
  GET /api/v1/admin/cron-runs/health 최근 실행 기준 health 요약 (외부 모니터링 ping 용)

설계:
  - read-only DuckDB 조회 — write 락 없음.
  - 인증 없음 (운영 환경에서는 ALLOWED_HOSTS / 내부망 차단으로 보호 권장).
  - cron 실행을 적재하는 헬퍼는 `Back/MachineLearning/cron_telemetry.py`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services._core import con as _con


router = APIRouter(prefix="/admin", tags=["admin"])


class CronRunItem(BaseModel):
    run_id:        str
    step:          str
    started_at:    Optional[str] = None
    ended_at:      Optional[str] = None
    status:        str
    error_class:   Optional[str] = None
    error_message: Optional[str] = None
    rows_affected: Optional[int] = None
    duration_sec:  Optional[float] = None


class CronRunsResponse(BaseModel):
    total: int
    items: List[CronRunItem]


@router.get("/cron-runs", response_model=CronRunsResponse, summary="최근 cron/배치 실행 이력")
def list_cron_runs(
    limit: int = Query(50, ge=1, le=500),
    step:  Optional[str] = Query(None, description="step 이름 prefix 필터"),
    status: Optional[str] = Query(None, pattern="^(ok|failed|no_change|running)$"),
):
    """started_at 기준 최신순으로 cron_runs 행 반환."""
    try:
        c = _con()
        where = ["1=1"]
        params: list = []
        if step:
            where.append("step LIKE ?")
            params.append(step + "%")
        if status:
            where.append("status = ?")
            params.append(status)
        rows = c.execute(
            f"""
            SELECT run_id, step,
                   CAST(started_at AS VARCHAR) AS started_at,
                   CAST(ended_at   AS VARCHAR) AS ended_at,
                   status, error_class, error_message,
                   rows_affected, duration_sec
            FROM cron_runs
            WHERE {' AND '.join(where)}
            ORDER BY started_at DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()
    except Exception as e:
        # cron_runs 테이블 자체가 없으면 503 (옛 환경)
        raise HTTPException(status_code=503, detail=f"cron_runs 조회 실패: {type(e).__name__}")

    items = [
        CronRunItem(
            run_id=r[0], step=r[1],
            started_at=r[2], ended_at=r[3],
            status=r[4], error_class=r[5], error_message=r[6],
            rows_affected=r[7], duration_sec=float(r[8]) if r[8] is not None else None,
        )
        for r in rows
    ]
    return CronRunsResponse(total=len(items), items=items)


class CronHealthResponse(BaseModel):
    status: str                      # ok / degraded / stale / unknown
    message: str
    last_run_at: Optional[str] = None
    failed_24h: int = 0
    running_now: int = 0
    summary: dict = {}


@router.get("/cron-runs/health", response_model=CronHealthResponse,
            summary="cron health 요약 (외부 모니터 ping 용)")
def cron_health(stale_hours: int = Query(24, ge=1, le=168)):
    """최근 24h 내 실행이 있고, 실패 없으면 'ok'.
    `stale_hours` 이상 실행 없으면 'stale', 실패가 있으면 'degraded'.
    """
    try:
        c = _con()
        row = c.execute(
            """
            SELECT
                CAST(MAX(started_at) AS VARCHAR) AS last_at,
                SUM(CASE WHEN status='failed'
                          AND started_at > CURRENT_TIMESTAMP - INTERVAL '24' HOUR
                         THEN 1 ELSE 0 END) AS failed_24h,
                SUM(CASE WHEN status='running' THEN 1 ELSE 0 END) AS running_now,
                COUNT(*) AS total_rows
            FROM cron_runs
            """
        ).fetchone()
    except Exception as e:
        return CronHealthResponse(
            status="unknown",
            message=f"cron_runs 미존재 또는 조회 실패: {type(e).__name__}",
        )

    last_at  = row[0]
    failed   = int(row[1] or 0)
    running  = int(row[2] or 0)
    total    = int(row[3] or 0)

    if total == 0:
        return CronHealthResponse(
            status="unknown",
            message="cron_runs 비어있음 — 아직 한 번도 실행 안 됨",
            failed_24h=0, running_now=0,
            summary={"total_rows": 0},
        )

    # stale 판단: 마지막 started_at 이 stale_hours 보다 오래됐는지.
    stale = False
    if last_at:
        try:
            last = datetime.fromisoformat(last_at.replace(" ", "T"))
            cutoff = datetime.now() - timedelta(hours=stale_hours)
            stale = last < cutoff
        except Exception:
            stale = False

    if failed > 0:
        status = "degraded"
        msg = f"최근 24h 내 {failed}건 실패 — 운영 로그 확인 필요"
    elif stale:
        status = "stale"
        msg = f"마지막 실행이 {stale_hours}h 이상 과거 — 배치 스케줄 점검 필요"
    else:
        status = "ok"
        msg = "최근 실행 정상"

    return CronHealthResponse(
        status=status, message=msg, last_run_at=last_at,
        failed_24h=failed, running_now=running,
        summary={"total_rows": total},
    )

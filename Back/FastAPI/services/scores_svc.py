"""
services/scores_svc.py
======================
Tier 1B 4.5 (CLAUDE.md §3.0) — `data.py` 분할 결과물.

scores 테이블 + KOSPI 레짐 + 자동 포트폴리오 도메인.
함수:
  - get_recommendations / get_stock_history / get_sector_summary
  - search_stocks / screen_stocks / compare_stocks
  - get_market_regime / get_kospi200_portfolio
"""

from __future__ import annotations

import pandas as pd

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
    get_latest_date as _get_latest_date,
)
from ._helpers import mark_bubble_stocks
from .signal_label import attach_signal_labels
from .star_rating import attach_star_ratings
from .headline import attach_headlines


def _attach_change_pct(items: list[dict]) -> list[dict]:
    """추천/검색 결과에 전일 대비 등락률 `change_pct` 필드 부착.

    prices 테이블의 직전 거래일 종가를 조회해 일괄 계산.
    실패 시 0 으로 폴백 (graceful).
    """
    if not items:
        return items
    try:
        tickers = list({it["ticker"] for it in items if it.get("ticker")})
        if not tickers:
            return items
        placeholders = ",".join(["?"] * len(tickers))
        con = _con()
        # 각 ticker 의 마지막 두 거래일 종가
        rows = con.execute(
            f"""
            WITH ranked AS (
              SELECT ticker, close,
                     ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
              FROM prices WHERE ticker IN ({placeholders})
            )
            SELECT ticker,
                   MAX(CASE WHEN rn = 1 THEN close END) AS today_close,
                   MAX(CASE WHEN rn = 2 THEN close END) AS prev_close
            FROM ranked WHERE rn <= 2 GROUP BY ticker
            """,
            tickers,
        ).fetchall()
        diff_map = {}
        for ticker, today_c, prev_c in rows:
            if today_c and prev_c and float(prev_c) > 0:
                diff_map[ticker] = round((float(today_c) - float(prev_c)) / float(prev_c) * 100, 2)
        # diff_map 에 없는 ticker 는 prices 가 1일치만 있거나 미수집 — null 로 유지하여
        # FE 가 "데이터 없음"과 "변동 없음(0.0%)"을 구분할 수 있게 한다.
        for it in items:
            it["change_pct"] = diff_map.get(it.get("ticker"))
    except Exception:
        for it in items:
            it.setdefault("change_pct", None)
    return items


def _norm_optional_str(val: str | None) -> str | None:
    """쿼리·캐시 키용: 빈 문자열과 공백만 있는 값은 None 으로 통일."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _get_kospi_regime(con, ref_date: str, ma_window: int = 20) -> int:
    """
    ref_date 기준 KOSPI 20일 MA 레짐 계산.
    prices 테이블의 삼성전자(005930) 종가를 KOSPI 프록시로 사용.
    Returns: 1=상승(정상), 0=하락(방어)
    """
    try:
        ref_int = int(ref_date.replace("-", ""))
        rows = con.execute(
            """
            SELECT date, close
            FROM prices
            WHERE ticker = '005930' AND date <= ?
            ORDER BY date DESC
            LIMIT ?
            """,
            [ref_int, ma_window * 2],
        ).fetchdf()
        if rows.empty or len(rows) < 5:
            return 1
        rows = rows.sort_values("date")
        ma = rows["close"].rolling(min(ma_window, len(rows)), min_periods=3).mean().iloc[-1]
        last = float(rows["close"].iloc[-1])
        return 1 if last >= ma else 0
    except Exception:
        return 1


def get_recommendations(
    date: str | None = None,
    model_version: str = "latest",
    sector: str | None = None,
    top_k: int = 20,
    min_score: float = 0.0,
    strategy: str = "base",
) -> list[dict]:
    """
    날짜별 종목 추천 목록 (score 내림차순).

    - date=None   → 가장 최신 날짜
    - top_k=0     → 전체 반환
    - strategy    → "base"(기본) | "s3"(v9 S3: prob Top-150 + 레짐 신호 포함)
    """
    date_key = _norm_optional_str(date)
    sector_key = _norm_optional_str(sector)
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        # 날짜 결정 — None 또는 빈 문자열이면 최신 날짜 사용
        _date = date_key
        if _date is None:
            _date = _get_latest_date(ver)

        if _date is None:
            return []

        conditions = ["model_version = ?", "CAST(date AS VARCHAR) = ?", "score >= ?"]
        params: list = [ver, _date, min_score]

        if sector_key:
            conditions.append("sector = ?")
            params.append(sector_key)

        # S3 전략: prob 상위 기준, top_k를 150으로 고정
        _top_k = 150 if strategy == "s3" else top_k
        limit_clause = f"LIMIT {int(_top_k)}" if _top_k > 0 else ""

        # Tier 1.3: top_factors 컬럼은 compute_shap.py 가 ALTER TABLE 로 추가.
        # 컬럼이 아직 없는 환경에서도 동작하도록 동적으로 SELECT 절을 구성.
        cols_in_scores = {row[1] for row in con.execute("PRAGMA table_info('scores')").fetchall()}
        has_top_factors = "top_factors" in cols_in_scores
        top_factors_select = "s.top_factors," if has_top_factors else ""

        # B1: cohort 가중치(conservative/dividend/value/growth) 가 실효되려면 per/pbr/
        # dividend_yield/roe 가 응답에 있어야 한다. 최신 분기 finance LEFT JOIN.
        # B60: illiquid 종목 (최근 5일 거래량 평균 0 또는 매우 낮음) 제외 — 추천해도
        # 실제 매수 체결 불가. 사용자 화면에 "변동률 0%" 다수 출현 원인.
        sql = f"""
            WITH latest_finance AS (
                SELECT f.ticker, f.per, f.pbr, f.dividend_yield, f.roe, f.debt_ratio,
                       f.op_margin, f.net_margin, f.rev_growth_yoy
                FROM finance f
                INNER JOIN (
                    SELECT ticker, MAX(year * 10 + quarter) AS yq_max
                    FROM finance
                    WHERE per IS NOT NULL OR pbr IS NOT NULL OR dividend_yield IS NOT NULL
                       OR roe IS NOT NULL OR rev_growth_yoy IS NOT NULL
                    GROUP BY ticker
                ) lf ON f.ticker = lf.ticker AND (f.year * 10 + f.quarter) = lf.yq_max
            ),
            recent_liquidity AS (
                -- B60: ticker 별 최근 5거래일 평균 거래량. 0 이면 illiquid → 제외.
                SELECT ticker, AVG(volume) AS avg_vol_5d
                FROM (
                    SELECT ticker, volume,
                        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                    FROM prices
                ) WHERE rn <= 5
                GROUP BY ticker
            )
            SELECT
                CAST(s.date AS VARCHAR)            AS date,
                s.ticker,
                COALESCE(s.name, st.name)          AS name,
                COALESCE(s.sector, st.wics_large_name) AS sector,
                s.mid_sector,
                s.close,
                ROUND(s.prob_lgbm, 6)              AS prob_lgbm,
                ROUND(s.prob_xgb,  6)              AS prob_xgb,
                ROUND(s.prob_cat,  6)              AS prob_cat,
                ROUND(s.prob_ensemble, 6)          AS prob_ensemble,
                ROUND(CAST(s.score AS DOUBLE), 1)  AS score,
                s.tier,
                s.rank_in_date,
                s.total_in_date,
                s.model_version,
                lfin.per, lfin.pbr, lfin.dividend_yield, lfin.roe, lfin.debt_ratio,
                lfin.op_margin, lfin.net_margin, lfin.rev_growth_yoy,
                {top_factors_select}
                NULL AS _placeholder
            FROM scores s
            LEFT JOIN stocks st         ON s.ticker = st.ticker
            LEFT JOIN latest_finance lfin ON s.ticker = lfin.ticker
            LEFT JOIN recent_liquidity rl ON s.ticker = rl.ticker
            WHERE {' AND '.join(conditions)}
              AND COALESCE(rl.avg_vol_5d, 0) >= 1000   -- B60: illiquid 제외 (5일 평균 1,000주 미만)
            ORDER BY s.score DESC
            {limit_clause}
        """
        rows = con.execute(sql, params).fetchdf()
        if "_placeholder" in rows.columns:
            rows = rows.drop(columns=["_placeholder"])
        result = rows.to_dict(orient="records")

        # B53 — prob_ensemble alias 부착 (의미 명확: v11 = raw lambdarank score).
        for r in result:
            r["ml_rank_score"] = r.get("prob_ensemble")

        # top_factors VARCHAR(JSON) → list[dict] 로 변환 (Tier 1.3).
        if has_top_factors:
            import json as _json
            for r in result:
                tf = r.get("top_factors")
                if isinstance(tf, str) and tf:
                    try:
                        r["top_factors"] = _json.loads(tf)
                    except Exception:
                        r["top_factors"] = None
                elif tf is None or (isinstance(tf, float) and tf != tf):  # NaN
                    r["top_factors"] = None

        # S3 전략: 레짐 신호를 각 종목에 메타데이터로 부착
        if strategy == "s3":
            regime = _get_kospi_regime(con, _date)
            for r in result:
                r["regime"] = regime
                r["regime_label"] = "상승" if regime == 1 else "하락(방어)"
                # 하락 구간 경고: 실제 포지션 축소는 클라이언트 측에서 처리
                r["position_scale"] = 1.0 if regime == 1 else 0.5

        # B54: signal_label multi-factor — fair_value band 부착 후 attach_signal_labels.
        # 정확한 band 는 stocks/{ticker}/fairvalue 엔드포인트. 여기선 PER>100 or PBR>10 단순 추정.
        mark_bubble_stocks(result)

        # B10: 단일 SQL 로 모든 ticker 의 outcome 부착 — N+1 회피.
        # B65: outcomes (cumulative_return_pct = 30d 모멘텀) 를 signal_label 보다 먼저 부착.
        # signal_label 이 모멘텀 음수면 BUY → HOLD 강등하기 위해 순서 중요.
        from .outcomes_svc import attach_outcomes_batch as _attach_outcomes
        _attach_outcomes(result, model_version=ver)
        # P0-1 (PRD §8.1): score+tier+fair_band+momentum → 4단계 행동 라벨 부착 (B54+B65)
        attach_signal_labels(result)
        # P1-7 (PRD §8.1): 별점 + 동종 섹터 백분위
        attach_star_ratings(result, model_version=ver)
        # P1-10 (PRD §8.1): SHAP TopFactors 기반 헤드라인 한 줄
        attach_headlines(result)
        # 정합성 보강: 전일 대비 등락률 (FE change_pct 매핑)
        _attach_change_pct(result)

        return result

    return _cached(
        "recommendations", fetch,
        date=date_key, model_version=ver,
        sector=sector_key, top_k=top_k, min_score=min_score, strategy=strategy,
    )


def get_stock_history(
    ticker: str,
    model_version: str = "latest",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """특정 종목의 날짜별 스코어 이력."""
    ver = _resolve_version(model_version)
    t_hist = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        conditions = ["s.model_version = ?", "s.ticker = ?"]
        params: list = [ver, t_hist]

        if start_date:
            conditions.append("CAST(s.date AS VARCHAR) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("CAST(s.date AS VARCHAR) <= ?")
            params.append(end_date)

        # prices 테이블(date 는 INTEGER YYYYMMDD)을 조인해 OHLCV·시총 부착.
        sql = f"""
            SELECT
                CAST(s.date AS VARCHAR)                AS date,
                s.ticker,
                COALESCE(s.name, st.name)              AS name,
                COALESCE(s.sector, st.wics_large_name) AS sector,
                s.close,
                p.open, p.high, p.low, p.volume,
                p.market_cap, p.shares_outstanding, p.foreign_ratio,
                ROUND(s.prob_ensemble, 6)              AS prob_ensemble,
                ROUND(CAST(s.score AS DOUBLE), 1)      AS score,
                s.tier,
                s.rank_in_date,
                s.total_in_date,
                s.model_version
            FROM scores s
            LEFT JOIN stocks st ON s.ticker = st.ticker
            LEFT JOIN prices p
                   ON p.ticker = s.ticker
                  AND p.date = CAST(REPLACE(CAST(s.date AS VARCHAR), '-', '') AS INTEGER)
            WHERE {' AND '.join(conditions)}
            ORDER BY s.date
        """
        rows = con.execute(sql, params).fetchdf()
        return rows.to_dict(orient="records")

    return _cached(
        "stock_history", fetch,
        ticker=t_hist, model_version=ver,
        start_date=start_date, end_date=end_date,
    )


def get_sector_summary(
    date: str | None = None,
    model_version: str = "latest",
) -> list[dict]:
    """섹터별 평균 점수 요약 (특정 날짜 기준)."""
    date_key = _norm_optional_str(date)
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        _date = date_key
        if _date is None:
            _date = _get_latest_date(ver)

        if _date is None:
            return []

        sql = """
            SELECT
                COALESCE(sector, '미분류') AS sector,
                COUNT(*)                   AS stock_count,
                ROUND(AVG(score), 1)       AS avg_score,
                ROUND(MAX(score), 1)       AS max_score,
                ROUND(MIN(score), 1)       AS min_score,
                SUM(CASE WHEN tier='A' THEN 1 ELSE 0 END) AS tier_a_count,
                CAST(date AS VARCHAR)      AS date,
                model_version
            FROM scores
            WHERE model_version = ? AND CAST(date AS VARCHAR) = ?
            GROUP BY sector, date, model_version
            ORDER BY avg_score DESC
        """
        rows = con.execute(sql, [ver, _date]).fetchdf()
        return rows.to_dict(orient="records")

    return _cached("sector_summary", fetch, date=date_key, model_version=ver)


def batch_diagnosis(
    tickers: list[str],
    model_version: str = "latest",
) -> dict:
    """P1-12 (PRD §8.1) — 원스톱 진단. 다중 종목에 대한 일괄 점수/티어/신호/별점 리포트.

    응답:
      {
        date, model_version, total, summary: {avg_score, tier_distribution, signal_distribution},
        items: [
          {ticker, name, sector, score, tier, signal_label, star_rating,
           cumulative_return_pct, percentile_in_sector}, ...
        ],
        missing: [tickers_not_found]
      }
    """
    from .signal_label import attach_signal_labels
    from .star_rating import attach_star_ratings
    from .outcomes_svc import attach_outcomes

    ver = _resolve_version(model_version)

    # 입력 정규화
    norm = []
    for raw in (tickers or [])[:200]:
        s = str(raw or "").strip()
        if not s:
            continue
        norm.append(s.zfill(6) if s.isdigit() else s.upper())
    if not norm:
        return {"date": None, "model_version": ver, "total": 0,
                "summary": {}, "items": [], "missing": []}

    def fetch():
        con = _con()
        latest = _get_latest_date(ver)
        if not latest:
            return {"date": None, "model_version": ver, "total": 0,
                    "summary": {}, "items": [], "missing": list(norm)}

        cols = {row[1] for row in con.execute("PRAGMA table_info('scores')").fetchall()}
        has_top_factors = "top_factors" in cols
        tf_col = "s.top_factors," if has_top_factors else ""

        placeholders = ",".join(["?"] * len(norm))
        sql = f"""
            SELECT
                s.ticker,
                s.name,
                s.sector,
                s.mid_sector,
                ROUND(CAST(s.score AS DOUBLE), 1) AS score,
                s.tier,
                s.close,
                {tf_col}
                NULL AS _placeholder
            FROM scores s
            WHERE s.model_version=? AND CAST(s.date AS VARCHAR)=?
              AND s.ticker IN ({placeholders})
            ORDER BY s.score DESC
        """
        params = [ver, latest] + norm
        rows = con.execute(sql, params).fetchdf()
        if "_placeholder" in rows.columns:
            rows = rows.drop(columns=["_placeholder"])
        items = rows.to_dict(orient="records")

        # top_factors JSON 파싱
        if has_top_factors:
            for r in items:
                tf = r.get("top_factors")
                if isinstance(tf, str) and tf:
                    try:
                        r["top_factors"] = json.loads(tf)
                    except Exception:
                        r["top_factors"] = None

        # B65: outcomes 먼저 → signal_label 이 30d 모멘텀 음수면 BUY → HOLD 강등.
        attach_outcomes(items, model_version=ver)
        attach_signal_labels(items)
        attach_star_ratings(items, model_version=ver)

        # 요약 통계
        found_tickers = {r["ticker"] for r in items}
        missing = [t for t in norm if t not in found_tickers]

        if items:
            avg_score = round(sum(r["score"] for r in items if r.get("score") is not None) / len(items), 2)
            tier_dist = {}
            signal_dist = {}
            for r in items:
                t = r.get("tier") or "?"
                tier_dist[t] = tier_dist.get(t, 0) + 1
                sl = r.get("signal_label") or "?"
                signal_dist[sl] = signal_dist.get(sl, 0) + 1
            summary = {
                "avg_score":          avg_score,
                "tier_distribution":  tier_dist,
                "signal_distribution": signal_dist,
            }
        else:
            summary = {}

        return {
            "date":          latest,
            "model_version": ver,
            "total":         len(items),
            "summary":       summary,
            "items":         items,
            "missing":       missing,
        }

    return _cached("batch_diagnosis", fetch, ttl=120,
                   tickers="|".join(sorted(norm)), model_version=ver)


def get_peers(
    ticker: str,
    model_version: str = "latest",
    limit: int = 8,
) -> list[dict]:
    """P0-5 (PRD §8.1) — 자동 경쟁사 비교.

    기준 종목의 같은 섹터·**시가총액**(prices.market_cap = close × shares_outstanding,
    B2 fix) ±50% 종목을 점수 순으로 반환. 동일 섹터 우선, 부족하면 mid_sector 확대.
    """
    ver = _resolve_version(model_version)
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        latest = _get_latest_date(ver)
        if not latest:
            return []

        # B2 fix: 이전엔 'close' (주당 가격) 를 시가총액 프록시로 사용 →
        # 주가 5만원·시총 100조 / 주가 7.5만원·시총 1조 가 "비슷한 시총" 으로 묶임.
        # 실제 시가총액(prices.market_cap = close × shares_outstanding) 으로 교체.
        # latest_mc 서브쿼리는 가장 최근 일자 prices.market_cap 을 조회.
        base = con.execute(
            """
            SELECT s.ticker, s.name, s.sector, s.mid_sector, s.close, s.score, s.tier,
                   p.market_cap AS base_mc
            FROM scores s
            LEFT JOIN (
                SELECT ticker, market_cap, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                FROM prices
            ) p ON s.ticker = p.ticker AND p.rn = 1
            WHERE s.model_version=? AND CAST(s.date AS VARCHAR)=? AND s.ticker=?
            """,
            [ver, latest, t],
        ).fetchone()
        if not base:
            return []
        _, _, sector, mid_sector, close, _, _, base_mc = base

        # 시가총액 ±50% 범위. market_cap 없으면 필터 우회 (전 종목 허용).
        if base_mc and float(base_mc) > 0:
            mc_lo = float(base_mc) * 0.5
            mc_hi = float(base_mc) * 1.5
        else:
            mc_lo, mc_hi = 0.0, 1e18

        # 1차: 같은 sector + 시가총액 ±50% 유사 종목
        rows = con.execute(
            """
            WITH latest_mc AS (
                SELECT ticker, market_cap FROM (
                    SELECT ticker, market_cap,
                           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                    FROM prices
                ) WHERE rn = 1
            )
            SELECT
                s.ticker,
                s.name,
                s.sector,
                s.mid_sector,
                s.close,
                ROUND(CAST(s.score AS DOUBLE), 1) AS score,
                s.tier,
                ROUND(s.prob_ensemble, 6)         AS prob_ensemble,
                lmc.market_cap                    AS market_cap
            FROM scores s
            LEFT JOIN latest_mc lmc ON s.ticker = lmc.ticker
            WHERE s.model_version=?
              AND CAST(s.date AS VARCHAR)=?
              AND s.ticker != ?
              AND s.sector = ?
              AND COALESCE(lmc.market_cap, 0) BETWEEN ? AND ?
            ORDER BY s.score DESC
            LIMIT ?
            """,
            [ver, latest, t, sector or "", mc_lo, mc_hi, limit],
        ).fetchdf()

        # 2차: 부족하면 mid_sector 로 확대
        if len(rows) < limit and mid_sector:
            need = limit - len(rows)
            extra = con.execute(
                """
                SELECT
                    s.ticker, s.name, s.sector, s.mid_sector, s.close,
                    ROUND(CAST(s.score AS DOUBLE), 1) AS score,
                    s.tier,
                    ROUND(s.prob_ensemble, 6)         AS prob_ensemble
                FROM scores s
                WHERE s.model_version=?
                  AND CAST(s.date AS VARCHAR)=?
                  AND s.ticker != ?
                  AND s.mid_sector = ?
                  AND s.sector != ?
                ORDER BY s.score DESC
                LIMIT ?
                """,
                [ver, latest, t, mid_sector, sector or "", need],
            ).fetchdf()
            if not extra.empty:
                rows = pd.concat([rows, extra], ignore_index=True)

        # B65: 3차 fallback — 시총 ±50% 너무 좁아 peer 없는 종목 (현대모비스같이
        # *그 시총대* 종목 자체가 sector 내 부재) → 시총 무관 같은 sector 전체.
        if len(rows) < limit:
            need = limit - len(rows)
            extra2 = con.execute(
                """
                WITH latest_mc AS (
                    SELECT ticker, market_cap FROM (
                        SELECT ticker, market_cap,
                               ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                        FROM prices
                    ) WHERE rn = 1
                )
                SELECT
                    s.ticker, s.name, s.sector, s.mid_sector, s.close,
                    ROUND(CAST(s.score AS DOUBLE), 1) AS score,
                    s.tier,
                    ROUND(s.prob_ensemble, 6) AS prob_ensemble,
                    lmc.market_cap AS market_cap
                FROM scores s
                LEFT JOIN latest_mc lmc ON s.ticker = lmc.ticker
                WHERE s.model_version=? AND CAST(s.date AS VARCHAR)=?
                  AND s.ticker != ? AND s.sector = ?
                ORDER BY s.score DESC LIMIT ?
                """,
                [ver, latest, t, sector or "", need],
            ).fetchdf()
            if not extra2.empty:
                # 이미 포함된 ticker 중복 제거 + NaN 정리 (JSON 직렬화 안전)
                if not rows.empty:
                    extra2 = extra2[~extra2["ticker"].isin(rows["ticker"])]
                rows = pd.concat([rows, extra2.head(need)], ignore_index=True)

        # B65 + B64-bis: pd.NaN → None (JSON 직렬화 안전)
        rows = rows.where(rows.notna(), None)

        result = rows.to_dict(orient="records")
        attach_signal_labels(result)
        return result

    return _cached("peers", fetch, ttl=300, ticker=t, model_version=ver, limit=limit)


def search_stocks(
    q: str,
    model_version: str = "latest",
    limit: int = 20,
) -> list[dict]:
    """티커·회사명 키워드 검색 — 최신 날짜 ML 점수 포함."""
    ver = _resolve_version(model_version)

    def fetch():
        from ..core.security import escape_like
        con = _con()
        # Tier 1B 4.4: `%` 입력으로 전수 조회 방지.
        keyword = f"%{escape_like(q)}%"
        # B64 — cross-page MISMATCH fix: /rating 이 search_stocks 호출 후 signal 매김.
        # search_stocks 에 per/pbr 없으면 fair_band 검사 못함 → 거품주가 BUY 라벨 받음
        # (엠로 PER 294배인데 /rating=BUY, /recommendations=WATCH 모순).
        # 해결: latest_finance JOIN + per/pbr 부착 → attach_signal_labels 가 거품 차단.
        sql = """
            WITH latest_finance AS (
                SELECT f.ticker, f.per, f.pbr
                FROM finance f
                INNER JOIN (
                    SELECT ticker, MAX(year*10+quarter) AS yq
                    FROM finance WHERE per IS NOT NULL OR pbr IS NOT NULL
                    GROUP BY ticker
                ) m ON f.ticker=m.ticker AND f.year*10+f.quarter=m.yq
            )
            SELECT
                s.ticker,
                s.name,
                s.sector,
                s.mid_sector,
                s.close,
                ROUND(CAST(s.score AS DOUBLE), 1) AS score,
                s.tier,
                s.model_version,
                CAST(s.date AS VARCHAR) AS latest_date,
                lf.per, lf.pbr
            FROM scores s
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM scores
                WHERE model_version = ?
                GROUP BY ticker
            ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date
            LEFT JOIN latest_finance lf ON s.ticker = lf.ticker
            WHERE s.model_version = ?
              AND (s.ticker ILIKE ? ESCAPE '\\' OR s.name ILIKE ? ESCAPE '\\')
            ORDER BY s.score DESC
            LIMIT ?
        """
        rows = con.execute(sql, [ver, ver, keyword, keyword, limit]).fetchdf()
        result = rows.to_dict(orient="records")
        # B64: 거품주 마킹
        mark_bubble_stocks(result)
        _attach_change_pct(result)     # 전일 대비 등락률
        # B68: search — change_pct=0 (illiquid 의심) 종목도 WATCH 처리.
        # search 는 사용자 검색이라 종목 자체 제외하지 않고 signal 만 다운.
        # fair_band 재사용 (multi-factor signal 룰이 거품과 동일 — WATCH 처리)
        for r in result:
            if r.get("change_pct") == 0 and not r.get("fair_band"):
                r["fair_band"] = "very_overvalued"   # illiquid → WATCH 트리거
                r["liquidity_warn"] = True           # FE 에 명시할 수 있는 별도 플래그
        attach_signal_labels(result)
        return result

    return _cached("search", fetch, ttl=120, q=q, model_version=ver, limit=limit)


def screen_stocks(
    model_version: str = "latest",
    min_score: float = 0.0,
    tier: str | None = None,
    sector: str | None = None,
    max_per: float | None = None,
    max_pbr: float | None = None,
    min_roe: float | None = None,
    max_debt_ratio: float | None = None,
    min_op_margin: float | None = None,
    min_rev_growth: float | None = None,
    min_finance_score: float | None = None,
    sort_by: str = "composite_score",
    limit: int = 50,
    ml_weight: float = 0.6,   # B11: composite 가중치 조절 가능 (기본 0.6)
) -> list[dict]:
    """ML 점수 + 재무 조건 복합 스크리너.

    B11: composite_score = ML × ml_weight + finance × (1 - ml_weight). 기본 0.6.
    """
    ver = _resolve_version(model_version)
    # 0~1 범위 강제 (라우터에서 이미 검증하지만 안전).
    ml_w  = max(0.0, min(1.0, float(ml_weight)))
    fin_w = round(1.0 - ml_w, 4)

    def fetch():
        con = _con()

        # 최신 날짜 결정
        latest_date = _get_latest_date(ver)

        if latest_date is None:
            return []

        # 최신 재무 분기 서브쿼리
        finance_sub = """
            SELECT
                f.ticker, f.name AS finance_name,
                f.per, f.pbr, f.roe, f.debt_ratio, f.op_margin,
                f.rev_growth_yoy, f.finance_score
            FROM finance f
            INNER JOIN (
                SELECT ticker, MAX(year*10+quarter) AS max_yq
                FROM finance GROUP BY ticker
            ) lf ON f.ticker = lf.ticker AND (f.year*10+f.quarter) = lf.max_yq
        """

        ml_conditions = ["s.model_version = ?", "CAST(s.date AS VARCHAR) = ?", "s.score >= ?"]
        params: list = [ver, latest_date, min_score]

        if tier:
            ml_conditions.append("s.tier = ?")
            params.append(tier.upper())
        if sector:
            ml_conditions.append("s.sector ILIKE ?")
            params.append(f"%{sector}%")

        # 재무 조건: 이전엔 f-string 으로 값 직접 삽입. float() 캐스트가 있어
        # 실제 SQL injection 은 차단되지만, 패턴이 위험하다. ? 바인딩으로 통일.
        finance_conditions = []
        if max_per is not None:
            finance_conditions.append("fi.per <= ?");          params.append(float(max_per))
        if max_pbr is not None:
            finance_conditions.append("fi.pbr <= ?");          params.append(float(max_pbr))
        if min_roe is not None:
            finance_conditions.append("fi.roe >= ?");          params.append(float(min_roe))
        if max_debt_ratio is not None:
            finance_conditions.append("fi.debt_ratio <= ?");   params.append(float(max_debt_ratio))
        if min_op_margin is not None:
            finance_conditions.append("fi.op_margin >= ?");    params.append(float(min_op_margin))
        if min_rev_growth is not None:
            finance_conditions.append("fi.rev_growth_yoy >= ?"); params.append(float(min_rev_growth))
        if min_finance_score is not None:
            finance_conditions.append("fi.finance_score >= ?"); params.append(float(min_finance_score))

        finance_where = ""
        if finance_conditions:
            finance_where = "AND " + " AND ".join(finance_conditions)

        # sort_by / limit 는 SQL identifier·LIMIT 자리라 ? 바인딩 불가.
        # → 화이트리스트 검사 후에만 f-string 에 삽입.
        ALLOWED_SORT = {"composite_score", "score", "finance_score", "roe", "per", "pbr", "rev_growth_yoy"}
        sort_col = sort_by if sort_by in ALLOWED_SORT else "composite_score"
        safe_limit = max(1, min(int(limit), 200))

        sql = f"""
            SELECT
                s.ticker,
                COALESCE(s.name, fi.finance_name)   AS name,
                s.sector,
                s.close,
                ROUND(CAST(s.score AS DOUBLE), 1)   AS score,
                s.tier,
                CAST(s.date AS VARCHAR)              AS latest_date,
                fi.per, fi.pbr, fi.roe, fi.debt_ratio,
                fi.op_margin, fi.rev_growth_yoy,
                ROUND(fi.finance_score, 1)           AS finance_score,
                ROUND(
                    CAST(s.score AS DOUBLE) * {ml_w}
                    + COALESCE(fi.finance_score, 50.0) * {fin_w},
                1)                                   AS composite_score
            FROM scores s
            LEFT JOIN ({finance_sub}) fi ON s.ticker = fi.ticker
            WHERE {' AND '.join(ml_conditions)} {finance_where}
            ORDER BY {sort_col} DESC NULLS LAST
            LIMIT {safe_limit}
        """
        rows = con.execute(sql, params).fetchdf()
        result = rows.to_dict(orient="records")
        # B64-bis: cross-page mismatch fix — 스크리너도 거품주 fair_band 마킹 후 attach.
        mark_bubble_stocks(result)
        attach_signal_labels(result)   # P0-1 (multi-factor)
        _attach_change_pct(result)     # 전일 대비 등락률
        return result

    return _cached(
        "screener", fetch, ttl=120,
        model_version=ver, min_score=min_score, tier=tier, sector=sector,
        max_per=max_per, max_pbr=max_pbr, min_roe=min_roe,
        max_debt_ratio=max_debt_ratio, min_op_margin=min_op_margin,
        min_rev_growth=min_rev_growth, min_finance_score=min_finance_score,
        sort_by=sort_by, limit=limit, ml_weight=ml_w,
    )


def compare_stocks(
    tickers: list[str],
    model_version: str = "latest",
    period_days: int = 365,
) -> list[dict]:
    """여러 종목 ML 점수 이력 + 최신 재무 비교."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        results = []
        from datetime import datetime as _dt, timedelta as _timedelta

        # scores 테이블의 최신 날짜 기준으로 period 계산
        max_date_str = _get_latest_date(ver)

        for t in tickers:
            # ML 점수 이력 — scores.date 기준 period 적용
            if period_days > 0 and max_date_str:
                max_date = _dt.strptime(max_date_str, "%Y-%m-%d").date()
                cutoff = (max_date - _timedelta(days=period_days)).strftime("%Y-%m-%d")
                date_cond = f"AND CAST(date AS VARCHAR) >= '{cutoff}'"
            else:
                date_cond = ""

            hist_sql = f"""
                SELECT
                    CAST(date AS VARCHAR) AS date,
                    ROUND(CAST(score AS DOUBLE), 1) AS score,
                    tier, name, sector
                FROM scores
                WHERE ticker = ? AND model_version = ? {date_cond}
                ORDER BY date ASC
            """
            hist = con.execute(hist_sql, [t, ver]).fetchdf()

            name   = hist["name"].iloc[-1]   if not hist.empty and "name"   in hist.columns else None
            sector = hist["sector"].iloc[-1] if not hist.empty and "sector" in hist.columns else None
            latest_score = float(hist["score"].iloc[-1]) if not hist.empty else None
            latest_tier  = str(hist["tier"].iloc[-1])    if not hist.empty else None
            score_history = (
                hist[["date", "score"]].to_dict(orient="records") if not hist.empty else []
            )

            # 최신 재무
            fin_sql = """
                SELECT per, pbr, roe, debt_ratio, op_margin,
                       rev_growth_yoy, finance_score, year, quarter
                FROM finance
                WHERE ticker = ?
                ORDER BY year DESC, quarter DESC
                LIMIT 1
            """
            fin = con.execute(fin_sql, [t]).fetchdf()
            finance = fin.to_dict(orient="records")[0] if not fin.empty else None

            # 미존재 ticker: scores 도 finance 도 없으면 응답 row 자체를 만들지 않는다.
            # 이전엔 모든 필드 null 인 row 가 200 응답에 섞여 들어가 FE 가 "유효 종목"으로
            # 오해하고 빈 카드를 렌더했다.
            if hist.empty and (fin is None or fin.empty):
                continue

            results.append({
                "ticker":        t,
                "name":          name,
                "sector":        sector,
                "latest_score":  latest_score,
                "tier":          latest_tier,
                "score_history": score_history,
                "finance":       finance,
            })

        return results

    return _cached(
        "compare", fetch, ttl=120,
        tickers=",".join(sorted(tickers)), model_version=ver, period_days=period_days,
    )


def get_market_regime(model_version: str = "latest") -> dict:
    """Tier A 비율 + KOSPI 일일 변화율로 현재 시장 국면을 판단.

    P0-4 (PRD §8.1) — 기존 3단계(greed/neutral/fear)를 5단계로 세분화하고
    0-100 마켓스코어를 함께 반환. 응답 호환을 위해 기존 status/weather 필드는 유지
    (5단계 status 값 그대로 노출 — greed/optimism/neutral/pessimism/panic).
    """
    from .market_events import (
        compute_market_score,
        classify_market_level,
        load_kospi_daily_change,
        load_kospi_weekly_change,
    )
    from ..core.config import DUCKDB_PATH as _DDB_M

    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        latest = _get_latest_date(ver)
        if not latest:
            raise RuntimeError(f"scores 데이터 없음 (model_version={ver})")

        row = con.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN tier='A' THEN 1 ELSE 0 END) AS tier_a
            FROM scores
            WHERE model_version=? AND CAST(date AS VARCHAR)=?
            """,
            [ver, latest],
        ).fetchone()
        total  = int(row[0] or 0)
        tier_a = int(row[1] or 0)
        ratio  = (tier_a / total * 100) if total else 0.0

        # B21: ratio 는 ML 백분위 구조상 ~20% 고정이라 base 신호 없음.
        # KOSPI 일일/주간 변화율 + 모델 평균 prob_ensemble (당일 시장 낙관도) 사용.
        daily_change  = load_kospi_daily_change(
            duckdb_path=str(_DDB_M), as_of_date=latest,
        )
        weekly_change = load_kospi_weekly_change(
            duckdb_path=str(_DDB_M), as_of_date=latest,
        )
        avg_prob_row = con.execute(
            """
            SELECT AVG(prob_ensemble) FROM scores
            WHERE model_version=? AND CAST(date AS VARCHAR)=?
              AND prob_ensemble IS NOT NULL
            """,
            [ver, latest],
        ).fetchone()
        avg_prob = float(avg_prob_row[0]) if avg_prob_row and avg_prob_row[0] is not None else None

        # 0-100 마켓스코어 + 5단계 분류
        score = compute_market_score(
            daily_change=daily_change,
            weekly_change=weekly_change,
            avg_prob=avg_prob,
        )
        level = classify_market_level(score)

        messages = {
            "panic":     "시장 공포 단계입니다. 현금 비중 확대와 보수적 접근이 필요합니다.",
            "pessimism": "비관 분위기가 우세합니다. 선별적 매수 + 변동성 주의.",
            "neutral":   "방향성 탐색 구간입니다. 선별적인 종목 접근이 필요합니다.",
            "optimism":  "낙관 분위기입니다. 상승 모멘텀을 활용한 투자가 유효합니다.",
            "greed":     "과욕 단계입니다. 단기 과열 위험 — 분할 매수와 차익 실현 검토.",
        }

        return {
            "date":          latest,
            "model_version": ver,
            "total_count":   total,
            "tier_a_count":  tier_a,
            "tier_a_ratio":  round(ratio, 2),
            "daily_change":  round(daily_change, 4) if daily_change is not None else None,
            # 5단계 — choicestock 벤치마크 호환 (status/status_ko/weather/mood/score)
            "status":        level["status"],
            "status_ko":     level["status_ko"],
            "weather":       level["weather"],
            "mood":          level["mood"],
            "market_score":  level["score"],
            "score_range":   level["score_range"],
            "message":       messages.get(level["status"], ""),
        }

    return _cached("market_regime", fetch, ttl=300, model_version=ver)


def get_kospi200_portfolio(
    portfolio_type: str = "growth",
    model_version: str = "latest",
) -> dict:
    """KOSPI 종목 중 사용자 성향에 맞는 Top 10 자동 포트폴리오.

    B13 주의: 이 함수의 universe 는 `seed.exchange = 'KOSPI'` 전체 (~1,500개) —
    진짜 KOSPI200 지수 구성종목 200개와는 다르다. 응답 메타에 `universe` 명시.

    - growth : score 상위 10
    - stable : Tier A·B + 최신 PBR이 **자기 섹터 평균 미만** → score 상위 10
              (B12 fix: 이전 `pbr < 1.5` 단일 cutoff → IT(평균>3) 종목 거의 다 제외,
               은행(평균<0.5) 거의 다 통과의 섹터 편향. 섹터 상대로 교체.)
    """
    from ..core.config import SEED_CSV
    ver        = _resolve_version(model_version)
    seed_path  = str(SEED_CSV).replace("\\", "/")
    is_stable  = (portfolio_type == "stable")

    def fetch():
        con = _con()
        latest = _get_latest_date(ver)
        if not latest:
            raise RuntimeError(f"scores 데이터 없음 (model_version={ver})")

        if is_stable:
            # B12: PBR 의 섹터 중앙값 대비 "더 낮은" 종목 선별.
            sql = f"""
                WITH last_finance AS (
                    SELECT ticker, MAX(year * 10 + quarter) AS yq_max
                    FROM finance
                    WHERE pbr IS NOT NULL
                    GROUP BY ticker
                ),
                fin_latest AS (
                    SELECT f.ticker, f.pbr
                    FROM finance f
                    INNER JOIN last_finance lf
                       ON f.ticker = lf.ticker AND (f.year * 10 + f.quarter) = lf.yq_max
                ),
                kospi_universe AS (
                    SELECT LPAD(CAST(seed.ticker AS VARCHAR), 6, '0') AS ticker
                    FROM read_csv_auto('{seed_path}') seed
                    WHERE seed.exchange = 'KOSPI'
                ),
                sector_pbr_med AS (
                    SELECT s.sector, MEDIAN(fl.pbr) AS sec_pbr_med
                    FROM scores s
                    INNER JOIN kospi_universe ku ON s.ticker = ku.ticker
                    INNER JOIN fin_latest fl     ON s.ticker = fl.ticker
                    WHERE s.model_version = ? AND CAST(s.date AS VARCHAR) = ?
                      AND fl.pbr > 0 AND fl.pbr < 30
                    GROUP BY s.sector
                )
                SELECT s.ticker, s.name, s.sector,
                       CAST(s.score AS FLOAT) AS score,
                       s.tier,
                       CAST(fl.pbr   AS FLOAT) AS pbr,
                       CAST(spm.sec_pbr_med AS FLOAT) AS sector_pbr_med
                FROM scores s
                INNER JOIN kospi_universe ku ON s.ticker = ku.ticker
                INNER JOIN fin_latest fl     ON s.ticker = fl.ticker
                LEFT  JOIN sector_pbr_med spm ON s.sector = spm.sector
                WHERE s.model_version = ?
                  AND CAST(s.date AS VARCHAR) = ?
                  AND s.tier IN ('A', 'B')
                  AND fl.pbr < COALESCE(spm.sec_pbr_med, 1.5)  -- 섹터 중앙값 미만, 매핑 부재 시 1.5 폴백
                ORDER BY s.score DESC
                LIMIT 10
            """
            df = con.execute(sql, [ver, latest, ver, latest]).fetchdf()
        else:  # growth
            sql = f"""
                SELECT s.ticker, s.name, s.sector,
                       CAST(s.score AS FLOAT) AS score,
                       s.tier
                FROM scores s
                INNER JOIN read_csv_auto('{seed_path}') seed
                    ON s.ticker = LPAD(CAST(seed.ticker AS VARCHAR), 6, '0')
                WHERE s.model_version = ?
                  AND CAST(s.date AS VARCHAR) = ?
                  AND seed.exchange = 'KOSPI'
                ORDER BY s.score DESC
                LIMIT 10
            """
            df = con.execute(sql, [ver, latest]).fetchdf()

        items = []
        for i, r in df.iterrows():
            item = {
                "rank":   i + 1,
                "ticker": r["ticker"],
                "name":   r.get("name"),
                "sector": r.get("sector"),
                "score":  float(r["score"]),
                "tier":   r["tier"],
                "pbr":    float(r["pbr"]) if is_stable and pd.notna(r.get("pbr")) else None,
                # B26: SQL 이 sector_pbr_med 를 SELECT 하지만 이전 응답에 미부착이라
                # 스키마 항상 None. stable 모드에서 노출 (FE 가 "섹터 평균 vs 본 종목" 비교 가능).
                "sector_pbr_med": float(r["sector_pbr_med"])
                    if is_stable and "sector_pbr_med" in r and pd.notna(r.get("sector_pbr_med")) else None,
            }
            items.append(item)

        return {
            "type":          portfolio_type,
            "date":          latest,
            "model_version": ver,
            "total":         len(items),
            "items":         items,
            # B13: 진짜 KOSPI200 지수 구성종목 200개가 아님을 명시.
            "universe":      "KOSPI_all",
            "universe_note": "KOSPI 전체 상장 종목(약 950개) 대상. 공식 KOSPI200 지수 구성과는 다름.",
        }

    return _cached(
        "kospi200_portfolio", fetch, ttl=300,
        portfolio_type=portfolio_type, model_version=ver,
    )

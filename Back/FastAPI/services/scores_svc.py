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

        sql = f"""
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
                {top_factors_select}
                NULL AS _placeholder
            FROM scores s
            LEFT JOIN stocks st ON s.ticker = st.ticker
            WHERE {' AND '.join(conditions)}
            ORDER BY s.score DESC
            {limit_clause}
        """
        rows = con.execute(sql, params).fetchdf()
        if "_placeholder" in rows.columns:
            rows = rows.drop(columns=["_placeholder"])
        result = rows.to_dict(orient="records")

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

        sql = f"""
            SELECT
                CAST(s.date AS VARCHAR)                AS date,
                s.ticker,
                COALESCE(s.name, st.name)              AS name,
                COALESCE(s.sector, st.wics_large_name) AS sector,
                s.close,
                ROUND(s.prob_ensemble, 6)              AS prob_ensemble,
                ROUND(CAST(s.score AS DOUBLE), 1)      AS score,
                s.tier,
                s.rank_in_date,
                s.total_in_date,
                s.model_version
            FROM scores s
            LEFT JOIN stocks st ON s.ticker = st.ticker
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
        sql = """
            SELECT
                s.ticker,
                s.name,
                s.sector,
                s.mid_sector,
                ROUND(CAST(s.score AS DOUBLE), 1) AS score,
                s.tier,
                s.model_version,
                CAST(s.date AS VARCHAR) AS latest_date
            FROM scores s
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM scores
                WHERE model_version = ?
                GROUP BY ticker
            ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date
            WHERE s.model_version = ?
              AND (s.ticker ILIKE ? ESCAPE '\\' OR s.name ILIKE ? ESCAPE '\\')
            ORDER BY s.score DESC
            LIMIT ?
        """
        rows = con.execute(sql, [ver, ver, keyword, keyword, limit]).fetchdf()
        return rows.to_dict(orient="records")

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
) -> list[dict]:
    """ML 점수 + 재무 조건 복합 스크리너."""
    ver = _resolve_version(model_version)

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

        finance_conditions = []
        if max_per is not None:
            finance_conditions.append(f"fi.per <= {float(max_per)}")
        if max_pbr is not None:
            finance_conditions.append(f"fi.pbr <= {float(max_pbr)}")
        if min_roe is not None:
            finance_conditions.append(f"fi.roe >= {float(min_roe)}")
        if max_debt_ratio is not None:
            finance_conditions.append(f"fi.debt_ratio <= {float(max_debt_ratio)}")
        if min_op_margin is not None:
            finance_conditions.append(f"fi.op_margin >= {float(min_op_margin)}")
        if min_rev_growth is not None:
            finance_conditions.append(f"fi.rev_growth_yoy >= {float(min_rev_growth)}")
        if min_finance_score is not None:
            finance_conditions.append(f"fi.finance_score >= {float(min_finance_score)}")

        finance_where = ""
        if finance_conditions:
            finance_where = "AND " + " AND ".join(finance_conditions)

        ALLOWED_SORT = {"composite_score", "score", "finance_score", "roe", "per", "pbr", "rev_growth_yoy"}
        sort_col = sort_by if sort_by in ALLOWED_SORT else "composite_score"

        sql = f"""
            SELECT
                s.ticker,
                COALESCE(s.name, fi.finance_name)   AS name,
                s.sector,
                ROUND(CAST(s.score AS DOUBLE), 1)   AS score,
                s.tier,
                CAST(s.date AS VARCHAR)              AS latest_date,
                fi.per, fi.pbr, fi.roe, fi.debt_ratio,
                fi.op_margin, fi.rev_growth_yoy,
                ROUND(fi.finance_score, 1)           AS finance_score,
                ROUND(
                    CAST(s.score AS DOUBLE) * 0.6
                    + COALESCE(fi.finance_score, 50.0) * 0.4,
                1)                                   AS composite_score
            FROM scores s
            LEFT JOIN ({finance_sub}) fi ON s.ticker = fi.ticker
            WHERE {' AND '.join(ml_conditions)} {finance_where}
            ORDER BY {sort_col} DESC NULLS LAST
            LIMIT {int(limit)}
        """
        rows = con.execute(sql, params).fetchdf()
        return rows.to_dict(orient="records")

    return _cached(
        "screener", fetch, ttl=120,
        model_version=ver, min_score=min_score, tier=tier, sector=sector,
        max_per=max_per, max_pbr=max_pbr, min_roe=min_roe,
        max_debt_ratio=max_debt_ratio, min_op_margin=min_op_margin,
        min_rev_growth=min_rev_growth, min_finance_score=min_finance_score,
        sort_by=sort_by, limit=limit,
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
    """Tier A 종목 비율로 현재 시장 국면(greed/neutral/fear)을 판단."""
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

        if ratio >= 10:
            status, weather, msg = "greed", "맑음", "상승 모멘텀이 강합니다. 적극적인 투자가 유리한 국면입니다."
        elif ratio >= 5:
            status, weather, msg = "neutral", "흐림", "방향성 탐색 구간입니다. 선별적인 종목 접근이 필요합니다."
        else:
            status, weather, msg = "fear", "비", "시장 변동성이 커지고 있습니다. 현금 비중 확대를 권장합니다."

        return {
            "date":          latest,
            "model_version": ver,
            "total_count":   total,
            "tier_a_count":  tier_a,
            "tier_a_ratio":  round(ratio, 2),
            "status":        status,
            "weather":       weather,
            "message":       msg,
        }

    return _cached("market_regime", fetch, ttl=300, model_version=ver)


def get_kospi200_portfolio(
    portfolio_type: str = "growth",
    model_version: str = "latest",
) -> dict:
    """KOSPI 종목 중 사용자 성향에 맞는 Top 10 자동 포트폴리오.

    - growth : score 상위 10
    - stable : Tier A·B + 최신 PBR < 1.5 → score 상위 10
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
            sql = f"""
                WITH last_finance AS (
                    SELECT ticker, MAX(year * 10 + quarter) AS yq_max
                    FROM finance
                    WHERE pbr IS NOT NULL
                    GROUP BY ticker
                )
                SELECT s.ticker, s.name, s.sector,
                       CAST(s.score AS FLOAT)  AS score,
                       s.tier,
                       CAST(f.pbr   AS FLOAT)  AS pbr
                FROM scores s
                INNER JOIN read_csv_auto('{seed_path}') seed
                    ON s.ticker = LPAD(CAST(seed.ticker AS VARCHAR), 6, '0')
                INNER JOIN last_finance lf
                    ON s.ticker = lf.ticker
                INNER JOIN finance f
                    ON f.ticker = lf.ticker AND (f.year * 10 + f.quarter) = lf.yq_max
                WHERE s.model_version = ?
                  AND CAST(s.date AS VARCHAR) = ?
                  AND seed.exchange = 'KOSPI'
                  AND s.tier IN ('A', 'B')
                  AND f.pbr < 1.5
                ORDER BY s.score DESC
                LIMIT 10
            """
            df = con.execute(sql, [ver, latest]).fetchdf()
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
            }
            items.append(item)

        return {
            "type":          portfolio_type,
            "date":          latest,
            "model_version": ver,
            "total":         len(items),
            "items":         items,
        }

    return _cached(
        "kospi200_portfolio", fetch, ttl=300,
        portfolio_type=portfolio_type, model_version=ver,
    )

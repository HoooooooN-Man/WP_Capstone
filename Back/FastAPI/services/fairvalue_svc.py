"""
services/fairvalue_svc.py
=========================
P2-13 (PRD §8.1) — 적정주가(Fair Value) 밴드차트.

설계 — 별도 ML 학습 없이 multiple 기반 추정. finance 테이블의 PER/PBR/EPS/BPS 활용:

  1. 동일 섹터의 PER·PBR 중앙값 추출 (시장 anchor)
  2. 종목 자체 4분기 PER·PBR 중앙값 추출 (자기 anchor)
  3. 적정가 = 평균(sector PER × EPS, sector PBR × BPS, 자기 PER × EPS, 자기 PBR × BPS)
  4. 현재가 vs 적정가 → 5단계 색대:
       deviation = (current - fair) / fair
       ≤ -30% → 매우저평가  (very_undervalued)
       ≤ -10% → 저평가      (undervalued)
       ≤ +10% → 적정        (fair)
       ≤ +30% → 고평가      (overvalued)
        >+30% → 매우고평가  (very_overvalued)

캡스톤 가이드: 룰 기반·투명·재현 가능. 실거래 자문 아님 (PRD §9 면책).
"""

from __future__ import annotations

from typing import Optional

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
    get_latest_date as _get_latest_date,
)


VALUATION_BANDS = [
    ("very_undervalued", "매우저평가", -1.00, -0.30),
    ("undervalued",      "저평가",     -0.30, -0.10),
    ("fair",             "적정",       -0.10,  0.10),
    ("overvalued",       "고평가",      0.10,  0.30),
    ("very_overvalued",  "매우고평가",   0.30,  1.00),
]

# B33: 섹터별 변동성 차이 반영 — IT/2차전지 같이 변동성 큰 섹터는 fair band 가
# 넓어야 정상 변동을 "고평가" 로 오분류하지 않는다. multiplier 가 1 보다 크면
# 밴드가 비례 확장 (예: 1.5 → fair = ±15%, overvalued cutoff 45%).
SECTOR_BAND_MULTIPLIER = {
    "IT":                 1.5,
    "전기·전자":           1.5,
    "2차전지":             1.6,
    "바이오":              1.7,
    "건강관리":            1.4,
    "통신서비스":          0.9,   # 안정 — 좁은 밴드
    "유틸리티":            0.8,
    "금융":                0.9,
    "은행":                0.9,
    "보험":                0.9,
}


def classify_valuation(deviation: float, sector: str | None = None) -> dict:
    """deviation (= (current - fair) / fair) → 5단계 라벨.

    B33: sector 가 주어지면 SECTOR_BAND_MULTIPLIER 로 밴드 폭 조정.
    """
    try:
        d = float(deviation)
    except (TypeError, ValueError):
        d = 0.0

    mult = SECTOR_BAND_MULTIPLIER.get(sector or "", 1.0) if sector else 1.0
    for code, ko, lo, hi in VALUATION_BANDS:
        if lo * mult <= d < hi * mult:
            return {"band": code, "band_ko": ko, "deviation": round(d * 100, 2)}
    # 경계값 처리
    if d >= 0.30 * mult:
        return {"band": "very_overvalued", "band_ko": "매우고평가", "deviation": round(d * 100, 2)}
    return {"band": "very_undervalued", "band_ko": "매우저평가", "deviation": round(d * 100, 2)}


SELF_MULTIPLE_CAP = 2.0   # B43: self_PER/PBR 가 sector × N 이상이면 outlier 로 캡. 3.0 → 2.0 (한미반도체같은 거품주 보수화).
MIN_EPS_FOR_PER  = 50.0   # B43: EPS 가 이 값 미만이면 적자/회계특이 → PER 기반 추정 제외.
MAX_IMPLIED_PER  = 200.0  # B46: 현재가/EPS > 200 = 진짜 적자/극단 거품 신호. 100 → 200 (self cap 으로 거품 충분 보수).


def compute_fair_value(
    eps: float | None,
    bps: float | None,
    sector_per: float | None,
    sector_pbr: float | None,
    self_per: float | None,
    self_pbr: float | None,
    current_price: float | None = None,
) -> Optional[float]:
    """multiple 기반 적정가 추정 — 자기/섹터 PER·PBR 4 추정 평균.

    설계 (B38+B43+B46):
      - **self_PER/PBR 캡**: sector multiple × 2 초과 분 → 캡 (한미반도체 64배 → 캡).
      - **적자/저수익 처리**: EPS < `MIN_EPS_FOR_PER` 면 PER 기반 추정 (est1, est3) 제외.
      - **거품주 처리** (B46): current_price/EPS > `MAX_IMPLIED_PER` 면 시장이 PER 로 평가
        안 한다는 신호 → PER 기반 추정 제외. 카카오 PER 192배, 엠로 PER 18배(TTM annualized) 같은 케이스.
      - **estimates 부족**: 모두 제외되면 None 반환.
    """
    # 적자/저수익/거품주 — PER 기반 추정 비활성
    use_per = eps is not None and eps >= MIN_EPS_FOR_PER
    if use_per and current_price is not None and eps > 0:
        implied_per = current_price / eps
        if implied_per > MAX_IMPLIED_PER:
            use_per = False

    # self multiple 캡
    if self_per is not None and sector_per is not None and sector_per > 0:
        self_per = min(float(self_per), sector_per * SELF_MULTIPLE_CAP)
    if self_pbr is not None and sector_pbr is not None and sector_pbr > 0:
        self_pbr = min(float(self_pbr), sector_pbr * SELF_MULTIPLE_CAP)

    estimates = []
    if use_per and sector_per is not None and sector_per > 0:
        estimates.append(eps * sector_per)
    if bps is not None and sector_pbr is not None and sector_pbr > 0 and bps > 0:
        estimates.append(bps * sector_pbr)
    if use_per and self_per is not None and self_per > 0:
        estimates.append(eps * self_per)
    if bps is not None and self_pbr is not None and self_pbr > 0 and bps > 0:
        estimates.append(bps * self_pbr)
    if not estimates:
        return None
    return sum(estimates) / len(estimates)


def get_fair_value(ticker: str) -> Optional[dict]:
    """단건 — 종목의 현재가 + 적정가 + 5단계 분류 + 추정 근거."""
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()

        # 현재가 (prices 최신 종가)
        cur = con.execute(
            """
            SELECT close, CAST(date AS VARCHAR) FROM prices
            WHERE ticker=? ORDER BY date DESC LIMIT 1
            """,
            [t],
        ).fetchone()
        if not cur:
            return None
        current_price = float(cur[0] or 0)
        current_date = cur[1]

        # B7 fix: 이전엔 최신 분기 단일 EPS 사용 — finance 분기 시차가 9개월일 수 있어
        # 적정가 추정의 EPS 가 너무 오래된 값일 수 있다. TTM(Trailing-Twelve-Months)
        # = 최근 4분기 합. Q4 행(연간 누적) 이 있으면 그 값을, 없으면 최근 분기 EPS 사용.
        # BPS 는 분기 말 스냅샷이라 합산하면 안 됨 → 최신 1개만.
        # 종목의 최신 분기 재무 + 섹터.
        fin = con.execute(
            """
            SELECT
                f.eps, f.bps, f.per, f.pbr,
                COALESCE(st.wics_large_name, st.wics_mid_name) AS sector,
                st.name,
                f.year, f.quarter
            FROM finance f
            LEFT JOIN stocks st ON f.ticker = st.ticker
            WHERE f.ticker = ?
              AND f.eps IS NOT NULL AND f.bps IS NOT NULL
            ORDER BY f.year DESC, f.quarter DESC
            LIMIT 1
            """,
            [t],
        ).fetchone()
        if not fin:
            return None
        eps_latest, bps, _self_per, _self_pbr, sector, name, fin_year, fin_quarter = fin

        # B41 TTM EPS 재설계 — 한국 finance 데이터는 *직전 annual EPS forward fill* 패턴.
        # 분기별 EPS 가 동일하면 stale (annual forward fill). 다르면 새 누적 실적 → 연환산.
        #   예) 삼성: 2024 Q1~Q4 모두 2,131 (annual 복사) → 2025 Q2 가 4,950 (H1 누적)
        #         → 4,950 ≠ 2,131 → 새 누적 → 4,950 × (4/2) = 9,900 (연환산)
        # 이전 로직은 q4 row 만 보면 1년 전 stale annual 사용 (삼성 2,131 → 적정가 52,589 폭락).
        ttm_row = con.execute(
            """
            SELECT eps, year, quarter FROM finance
            WHERE ticker = ? AND eps IS NOT NULL
            ORDER BY year DESC, quarter DESC LIMIT 6
            """,
            [t],
        ).fetchall()
        eps = None
        eps_method = "latest_quarter"
        if ttm_row:
            latest_eps, latest_year, latest_q = float(ttm_row[0][0]), int(ttm_row[0][1]), int(ttm_row[0][2])
            # B41 + B45 — fresh 비교는 *직전 분기* 와 해야 의미 있음.
            # 엠로처럼 prev 가 5분기 전 (gap > 2) 이면 비교 자체가 무의미 → carryover 보수.
            is_fresh = False
            if len(ttm_row) > 1:
                prev_eps = float(ttm_row[1][0])
                prev_year, prev_q = int(ttm_row[1][1]), int(ttm_row[1][2])
                gap = (latest_year - prev_year) * 4 + (latest_q - prev_q)
                if 0 < gap <= 2:
                    is_fresh = abs(latest_eps - prev_eps) / max(abs(prev_eps), 1.0) > 0.005

            if is_fresh and latest_q < 4:
                # B67: 누적(YTD) vs 단일 분기 자동 판별.
                # YTD 누적: Q3(누적) >= Q2(H1) — 시간이 흘러도 누적은 증가.
                # 단일 분기: 분기별 EPS 가 들쭉날쭉 (Q3 < Q2 가능).
                # 엠로 사례: Q2=1612(H1 누적), Q3=140 → Q3<<Q2 → 단일 분기 → × 4 annualize.
                # 삼성 사례: Q2=4950(H1), Q3=NULL or 다른 값 → 만약 누적 가정.
                is_ytd_cumulative = True
                if len(ttm_row) > 1 and latest_q > 1:
                    prev_eps_v = float(ttm_row[1][0])
                    # YTD 라면 latest 가 prev 이상 (누적). 미만이면 단일 분기 강력 시사.
                    if latest_eps < prev_eps_v * 0.6:
                        is_ytd_cumulative = False
                if is_ytd_cumulative:
                    annualize = {1: 4.0, 2: 2.0, 3: 4.0/3.0}.get(latest_q, 1.0)
                    eps_method = f"q{latest_q}_ytd_annualized"
                else:
                    annualize = 4.0   # 단일 분기 → × 4 (Q1×4 패턴)
                    eps_method = f"q{latest_q}_single_annualized"
                eps = latest_eps * annualize
            elif is_fresh and latest_q == 4:
                eps = latest_eps
                eps_method = "q4_annual_fresh"
            else:
                eps = latest_eps
                eps_method = "annual_carryover"

        # 자기 4분기 PER/PBR 중앙값 (이상치 완화) — 최근 4분기 만
        self_med = con.execute(
            """
            WITH last4 AS (
                SELECT per, pbr FROM finance
                WHERE ticker = ? AND per IS NOT NULL AND pbr IS NOT NULL
                ORDER BY year DESC, quarter DESC LIMIT 4
            )
            SELECT MEDIAN(per) FILTER (WHERE per > 0) AS self_per,
                   MEDIAN(pbr) FILTER (WHERE pbr > 0) AS self_pbr
            FROM last4
            """,
            [t],
        ).fetchone()
        self_per_med = float(self_med[0]) if self_med and self_med[0] is not None else None
        self_pbr_med = float(self_med[1]) if self_med and self_med[1] is not None else None

        # B50 narrow peer — 같은 섹터 + 시총 ±50% 범위 peer 만 사용.
        # NAVER 같은 대형 종목이 작은 sector 평균에 휘둘려 적정가 -47% 매우저평가로
        # 추정되는 문제 해결. base_mc 알 수 있으면 narrow, peer<5 면 broader fallback.
        # 시점: 현재가 기반 + 10~90 percentile trim + 시총가중 (B42+B44 유지).
        base_mc_row = con.execute(
            "SELECT market_cap FROM prices WHERE ticker=? AND market_cap > 0 ORDER BY date DESC LIMIT 1",
            [t],
        ).fetchone()
        base_mc = float(base_mc_row[0]) if base_mc_row and base_mc_row[0] else None

        sector_per = sector_pbr = None
        if sector:
            sql_peers = """
                WITH latest_finance AS (
                    SELECT f.ticker, f.eps, f.bps,
                        ROW_NUMBER() OVER (PARTITION BY f.ticker ORDER BY f.year DESC, f.quarter DESC) rn
                    FROM finance f
                    WHERE f.eps IS NOT NULL AND f.bps IS NOT NULL
                ),
                latest_price AS (
                    SELECT ticker, close, market_cap,
                        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                    FROM prices
                ),
                peers AS (
                    SELECT lf.ticker, lf.eps, lf.bps, lp.close, lp.market_cap,
                           CASE WHEN lf.eps > 0 THEN lp.close / lf.eps END AS per_now,
                           CASE WHEN lf.bps > 0 THEN lp.close / lf.bps END AS pbr_now
                    FROM latest_finance lf
                    INNER JOIN latest_price lp ON lf.ticker=lp.ticker AND lp.rn=1
                    LEFT JOIN stocks st ON lf.ticker=st.ticker
                    WHERE lf.rn=1
                      AND COALESCE(st.wics_large_name, st.wics_mid_name) = ?
                      AND lp.market_cap > 0
                      {mc_filter}
                ),
                per_bounds AS (
                    SELECT QUANTILE_CONT(per_now, 0.10) AS lo, QUANTILE_CONT(per_now, 0.90) AS hi
                    FROM peers WHERE per_now BETWEEN 1 AND 200
                ),
                pbr_bounds AS (
                    SELECT QUANTILE_CONT(pbr_now, 0.10) AS lo, QUANTILE_CONT(pbr_now, 0.90) AS hi
                    FROM peers WHERE pbr_now BETWEEN 0.1 AND 30
                )
                SELECT
                    COUNT(*) AS n_peers,
                    SUM(p.market_cap * p.per_now) FILTER (WHERE p.per_now BETWEEN pb.lo AND pb.hi)
                        / NULLIF(SUM(p.market_cap) FILTER (WHERE p.per_now BETWEEN pb.lo AND pb.hi), 0) AS sec_per_w,
                    SUM(p.market_cap * p.pbr_now) FILTER (WHERE p.pbr_now BETWEEN pbb.lo AND pbb.hi)
                        / NULLIF(SUM(p.market_cap) FILTER (WHERE p.pbr_now BETWEEN pbb.lo AND pbb.hi), 0) AS sec_pbr_w
                FROM peers p
                CROSS JOIN per_bounds pb
                CROSS JOIN pbr_bounds pbb
            """
            # 1차: narrow peer (시총 ±50% ~ ±100%)
            sec = None
            n_peers = 0
            if base_mc:
                mc_lo, mc_hi = base_mc * 0.5, base_mc * 2.0
                sql_narrow = sql_peers.format(mc_filter=f"AND lp.market_cap BETWEEN {mc_lo} AND {mc_hi}")
                row = con.execute(sql_narrow, [sector]).fetchone()
                if row and row[0] and int(row[0]) >= 5:
                    n_peers = int(row[0])
                    sec = (row[1], row[2])
            # 2차: 부족 시 전체 섹터 fallback
            if sec is None:
                sql_broad = sql_peers.format(mc_filter="")
                row = con.execute(sql_broad, [sector]).fetchone()
                if row:
                    n_peers = int(row[0]) if row[0] else 0
                    sec = (row[1], row[2])
            if sec:
                sector_per = float(sec[0]) if sec[0] is not None else None
                sector_pbr = float(sec[1]) if sec[1] is not None else None

        fair = compute_fair_value(
            eps=float(eps) if eps else None,
            bps=float(bps) if bps else None,
            sector_per=sector_per,
            sector_pbr=sector_pbr,
            self_per=self_per_med,
            self_pbr=self_pbr_med,
            current_price=current_price,
        )
        # B7: finance 시차 명시 (FE 가 "2025-Q2 재무 기준" 표시 가능).
        finance_as_of = f"{int(fin_year)}-Q{int(fin_quarter)}" if fin_year and fin_quarter else None
        if fair is None or fair <= 0:
            return None

        deviation = (current_price - fair) / fair
        band = classify_valuation(deviation, sector=sector)  # B33: 섹터별 밴드 폭

        return {
            "ticker":         t,
            "name":           name,
            "sector":         sector,
            "current_price":  round(current_price, 2),
            "current_date":   current_date,
            "fair_value":     round(fair, 2),
            "deviation_pct":  band["deviation"],
            "band":           band["band"],
            "band_ko":        band["band_ko"],
            "finance_as_of":  finance_as_of,
            "eps_method":     eps_method,   # B7+B24: ttm_annual_q4 | ttm_sum_4q | latest_quarter
            "inputs": {
                "eps":         float(eps) if eps else None,
                "bps":         float(bps) if bps else None,
                "sector_per":  round(sector_per, 2) if sector_per else None,
                "sector_pbr":  round(sector_pbr, 2) if sector_pbr else None,
                "self_per_med": round(self_per_med, 2) if self_per_med else None,
                "self_pbr_med": round(self_pbr_med, 2) if self_pbr_med else None,
            },
            "method":         "multiple_based",
            "is_advice":      False,
        }

    return _cached("fair_value", fetch, ttl=3600, ticker=t)


def get_fair_value_history(ticker: str, periods: int = 12) -> list[dict]:
    """월별 종가 vs 적정가 이력 (밴드차트용).

    분기별 finance + 월말 prices 종가 매칭. 캡스톤에서는 최근 N 분기만.
    """
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()

        # 섹터 조회 (B33: classify_valuation 에 sector 전달)
        sec_row = con.execute(
            """
            SELECT COALESCE(st.wics_large_name, st.wics_mid_name)
            FROM stocks st WHERE st.ticker = ? LIMIT 1
            """,
            [t],
        ).fetchone()
        sector = sec_row[0] if sec_row else None

        # B25: 단건 get_fair_value 는 TTM EPS 사용인데 history 는 단일분기 EPS 로
        # 다른 공식 → 차트 vs 현재값 불일치. 동일하게 TTM 적용.
        # 분기 finance 전체 불러와 각 분기 기준 TTM 계산.
        all_q = con.execute(
            """
            SELECT year, quarter, eps, bps, per, pbr, base_date
            FROM finance
            WHERE ticker = ? AND bps IS NOT NULL
            ORDER BY year ASC, quarter ASC
            """,
            [t],
        ).fetchall()
        if not all_q:
            return []

        # 인덱스 — (year, quarter) → row
        idx = {(int(r[0]), int(r[1])): r for r in all_q}

        # 각 분기에서 TTM 계산.
        result = []
        sorted_keys = sorted(idx.keys())
        # 최근 periods 분기만.
        target_keys = sorted_keys[-periods:]
        for yq in target_keys:
            year, quarter = yq
            base = idx[yq]
            _, _, eps_raw, bps, per, pbr, bdate = base
            # TTM EPS: 해당 분기까지의 직전 4분기 합 또는 Q4 단독.
            if quarter == 4 and eps_raw is not None:
                eps = float(eps_raw)
            else:
                last4 = []
                yy, qq = year, quarter
                for _ in range(4):
                    r = idx.get((yy, qq))
                    if r and r[2] is not None:
                        last4.append(float(r[2]))
                    qq -= 1
                    if qq == 0:
                        qq = 4
                        yy -= 1
                if len(last4) == 4:
                    eps = sum(last4)
                elif eps_raw is not None:
                    eps = float(eps_raw)
                else:
                    continue

            # 해당 분기 base_date 의 종가 — 별도 쿼리.
            close_row = con.execute(
                """
                SELECT close FROM prices
                WHERE ticker = ? AND date <= ?
                ORDER BY date DESC LIMIT 1
                """,
                [t, bdate],
            ).fetchone()
            close = float(close_row[0]) if close_row and close_row[0] else None

            ests = []
            if eps and per and float(per) > 0:
                ests.append(eps * float(per))
            if bps and pbr and float(pbr) > 0:
                ests.append(float(bps) * float(pbr))
            if not ests or not close:
                continue
            fair = sum(ests) / len(ests)
            dev = (close - fair) / fair if fair > 0 else 0
            band = classify_valuation(dev, sector=sector)  # B33
            result.append({
                "year":           int(year),
                "quarter":        int(quarter),
                "date":           str(bdate)[:10] if bdate else None,
                "close":          round(close, 2),
                "fair_value":     round(fair, 2),
                "deviation_pct":  band["deviation"],
                "band":           band["band"],
                "band_ko":        band["band_ko"],
            })
        return result

    return _cached("fair_value_history", fetch, ttl=3600, ticker=t, periods=periods)

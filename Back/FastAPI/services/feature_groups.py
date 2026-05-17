"""
services/feature_groups.py
==========================
P1-8 (PRD §8.1) — 73 features SHAP 값을 5 요인 그룹으로 합산해 레이더 차트 데이터 생성.

5 그룹 (choicestock 스마트스코어 벤치마크):
  - 성장성     (growth)     : 매출 성장률, EPS 성장률, 향후 가이던스 등
  - 수익성     (profitability): ROE, ROA, 영업이익률, 순이익률 등
  - 안전성     (safety)     : 부채비율, 유동비율, 이자보상배율 등
  - 독점력     (moat)       : 영업이익률 안정성, ROIC, 시장점유율 등
  - 현금창출력 (cashflow)   : 영업현금흐름, FCF, FCF/매출 비율 등

73 features 의 키워드 매칭으로 그룹 자동 분류. 매칭 실패 피처는 'macro' 분류로 별도 보관 (레이더 미반영).
SHAP 값 절댓값을 합산 후 5그룹 합계 = 100 으로 정규화 → 각 그룹 점수 0-100.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
    get_latest_date as _get_latest_date,
)


# 키워드 매칭 룰 (lowercased substring) — 우선순위는 dict 순서
FEATURE_GROUPS = {
    "growth": [
        "growth", "yoy", "qoq", "_growth", "revenue_growth", "eps_growth",
        "sales_growth", "rev_growth", "성장",
    ],
    "profitability": [
        "roe", "roa", "roic", "op_margin", "net_margin", "profit_margin",
        "operating_margin", "수익", "마진",
    ],
    "safety": [
        "debt", "leverage", "current_ratio", "quick_ratio", "interest_cov",
        "부채", "유동", "안전",
    ],
    "moat": [
        "stability", "consistency", "market_share", "moat", "독점", "안정성",
    ],
    "cashflow": [
        "cashflow", "fcf", "ocf", "cash_flow", "현금",
    ],
    "macro": [   # 매크로·외생변수 (레이더 미반영, 기타 그룹)
        "vix", "us_10y", "kospi", "fx_rate", "kor_3y", "macro",
    ],
}


def classify_feature(feature_name: str) -> str:
    """피처명 → 그룹명 (5그룹 중 하나 또는 'macro')."""
    name = (feature_name or "").lower()
    for group, keywords in FEATURE_GROUPS.items():
        for kw in keywords:
            if kw in name:
                return group
    return "macro"


def compute_radar_scores(top_factors: list[dict] | None) -> dict:
    """SHAP TopFactors → 5 그룹 점수 dict.

    top_factors 가 list 가 아닌 경우 (string JSON, None, NaN) graceful 처리.
    SHAP 값 절댓값을 합산 후 정규화 — 5 그룹 합계 = 100.
    """
    result = {g: 0.0 for g in ("growth", "profitability", "safety", "moat", "cashflow")}

    if isinstance(top_factors, str):
        try:
            top_factors = json.loads(top_factors)
        except Exception:
            top_factors = None

    if not isinstance(top_factors, list) or not top_factors:
        return result

    for f in top_factors:
        if not isinstance(f, dict):
            continue
        name = f.get("feature") or f.get("name") or ""
        # SHAP 절댓값
        raw = f.get("shap") if "shap" in f else f.get("value")
        try:
            val = abs(float(raw))
        except (TypeError, ValueError):
            continue
        group = classify_feature(name)
        if group in result:
            result[group] += val

    # 정규화 — 5 그룹 합계 = 100
    total = sum(result.values())
    if total > 0:
        for g in result:
            result[g] = round(result[g] / total * 100.0, 1)
    return result


_RADAR_GROUPS = ("growth", "profitability", "safety", "moat", "cashflow")


def _finance_radar_table() -> dict:
    """전 종목의 최근 분기 재무 → 5요인 백분위 점수 테이블 (캐시).

    `scores.top_factors` 는 US_10Y·VIX·fx_rate 등 매크로 피처 위주라 펀더멘털
    레이더로 부적합 → `finance` 테이블의 실제 재무 지표를 universe 백분위로 환산.

    매핑:
      - growth        : rev_growth_yoy, op_growth_yoy 백분위 평균
      - profitability : roe 백분위
      - safety        : debt_ratio(낮을수록 우수), current_ratio 백분위 평균
      - moat          : op_margin 백분위 (지속적 고마진 = 경쟁우위 proxy)
      - cashflow      : net_margin 백분위 (이익의 현금 전환력 proxy)

    반환: {"by_ticker": {ticker: {groups}}, "by_sector": {sector: {groups}}}
    """
    def fetch():
        con = _con()
        # B22+B23 fix: 이전엔 base CTE 가 "any non-null" 조건이라 일부 metric NULL row 가
        # rn=1 로 잡혀 NULLS FIRST → percentile=0 → 우량주가 최악 점수.
        # 새 설계: metric 별로 최근 non-null 값을 따로 추출 (LATEST_NONNULL_PER_METRIC),
        # 누락 metric 은 *percent_rank 에 포함시키지 않음* → NaN → Python 측에서 폴백 평균만 사용.
        rows = con.execute(
            """
            WITH ranked AS (
                SELECT
                    f.ticker,
                    f.year, f.quarter,
                    f.rev_growth_yoy, f.op_growth_yoy, f.roe,
                    f.debt_ratio, f.current_ratio, f.op_margin, f.net_margin,
                    ROW_NUMBER() OVER (PARTITION BY f.ticker, (f.rev_growth_yoy IS NULL) ORDER BY f.year DESC, f.quarter DESC) AS rn_rev,
                    ROW_NUMBER() OVER (PARTITION BY f.ticker, (f.op_growth_yoy  IS NULL) ORDER BY f.year DESC, f.quarter DESC) AS rn_opg,
                    ROW_NUMBER() OVER (PARTITION BY f.ticker, (f.roe            IS NULL) ORDER BY f.year DESC, f.quarter DESC) AS rn_roe,
                    ROW_NUMBER() OVER (PARTITION BY f.ticker, (f.debt_ratio     IS NULL) ORDER BY f.year DESC, f.quarter DESC) AS rn_debt,
                    ROW_NUMBER() OVER (PARTITION BY f.ticker, (f.current_ratio  IS NULL) ORDER BY f.year DESC, f.quarter DESC) AS rn_curr,
                    ROW_NUMBER() OVER (PARTITION BY f.ticker, (f.op_margin      IS NULL) ORDER BY f.year DESC, f.quarter DESC) AS rn_opm,
                    ROW_NUMBER() OVER (PARTITION BY f.ticker, (f.net_margin     IS NULL) ORDER BY f.year DESC, f.quarter DESC) AS rn_netm
                FROM finance f
            ),
            latest_metrics AS (
                SELECT
                    ticker,
                    MAX(CASE WHEN rn_rev  = 1 AND rev_growth_yoy IS NOT NULL THEN rev_growth_yoy END) AS rev_growth_yoy,
                    MAX(CASE WHEN rn_opg  = 1 AND op_growth_yoy  IS NOT NULL THEN op_growth_yoy  END) AS op_growth_yoy,
                    MAX(CASE WHEN rn_roe  = 1 AND roe            IS NOT NULL THEN roe            END) AS roe,
                    MAX(CASE WHEN rn_debt = 1 AND debt_ratio     IS NOT NULL THEN debt_ratio     END) AS debt_ratio,
                    MAX(CASE WHEN rn_curr = 1 AND current_ratio  IS NOT NULL THEN current_ratio  END) AS current_ratio,
                    MAX(CASE WHEN rn_opm  = 1 AND op_margin      IS NOT NULL THEN op_margin      END) AS op_margin,
                    MAX(CASE WHEN rn_netm = 1 AND net_margin     IS NOT NULL THEN net_margin     END) AS net_margin
                FROM ranked
                GROUP BY ticker
            )
            SELECT
                lm.ticker,
                COALESCE(st.wics_mid_name, '기타') AS sector,
                COALESCE(st.wics_large_name, st.wics_mid_name, '기타') AS sector_large,
                -- B22: NULLS FIRST 제거. NULL 은 percent_rank 가 NULL 반환 → Python 측에서 제외.
                CASE WHEN lm.rev_growth_yoy IS NULL THEN NULL
                     ELSE PERCENT_RANK() OVER (ORDER BY lm.rev_growth_yoy) * 100 END AS p_rev,
                CASE WHEN lm.op_growth_yoy IS NULL THEN NULL
                     ELSE PERCENT_RANK() OVER (ORDER BY lm.op_growth_yoy) * 100 END AS p_op_g,
                CASE WHEN lm.roe IS NULL THEN NULL
                     ELSE PERCENT_RANK() OVER (ORDER BY lm.roe) * 100 END AS p_roe,
                -- B48: 부채비율은 *섹터 내* 백분위. 금융업은 본업이 부채라 전체 universe 에서 항상 0점
                -- (하나금융 safety=0.6 같은 비현실 결과). PARTITION BY sector_large 로 섹터 내 비교.
                CASE WHEN lm.debt_ratio IS NULL THEN NULL
                     ELSE PERCENT_RANK() OVER (
                         PARTITION BY COALESCE(st.wics_large_name, st.wics_mid_name, '기타')
                         ORDER BY lm.debt_ratio DESC) * 100 END AS p_debt_inv,
                CASE WHEN lm.current_ratio IS NULL THEN NULL
                     ELSE PERCENT_RANK() OVER (
                         PARTITION BY COALESCE(st.wics_large_name, st.wics_mid_name, '기타')
                         ORDER BY lm.current_ratio) * 100 END AS p_curr,
                CASE WHEN lm.op_margin IS NULL THEN NULL
                     ELSE PERCENT_RANK() OVER (ORDER BY lm.op_margin) * 100 END AS p_opm,
                CASE WHEN lm.net_margin IS NULL THEN NULL
                     ELSE PERCENT_RANK() OVER (ORDER BY lm.net_margin) * 100 END AS p_netm
            FROM latest_metrics lm
            LEFT JOIN stocks st ON lm.ticker = st.ticker
            """
        ).fetchall()

        by_ticker: dict[str, dict] = {}
        sector_sums: dict[str, dict] = {}
        sector_cnt: dict[str, int] = {}

        def _avg_with_fallback(present, fallback=50.0):
            """non-null 값들 평균. 전부 None 이면 fallback(중립 50)."""
            vals = [float(x) for x in present if x is not None]
            return round(sum(vals) / len(vals), 1) if vals else fallback

        # B49 + B51: 금융업 safety — debt_ratio 무의미라 ROE 안정성 + 자본총계 percentile 사용.
        # 은행/보험은 *ROE 안정성* (지난 분기 ROE 변동성 낮음 = 안전) + *자본 규모* 가 본업 안전 proxy.
        # 본 모듈은 분기 시계열 미접근이라 단순화: 금융섹터에서 ROE percentile 자체를 safety proxy 로 사용
        # (ROE 가 안정적으로 양수면 본업 건전성 양호 시그널).
        FINANCIAL_SECTORS = {'금융', '은행', '증권', '보험'}
        for (tk, sector, sector_large, p_rev, p_op_g, p_roe, p_debt_inv, p_curr, p_opm, p_netm) in rows:
            is_financial = sector_large in FINANCIAL_SECTORS
            if is_financial:
                # 금융: safety = ROE percentile (수익 안정성 = 본업 건전성 proxy). 데이터 없으면 50.
                safety_val = _avg_with_fallback([p_roe], fallback=50.0)
            else:
                safety_val = _avg_with_fallback([p_debt_inv, p_curr])
            g = {
                "growth":        _avg_with_fallback([p_rev, p_op_g]),
                "profitability": _avg_with_fallback([p_roe]),
                "safety":        safety_val,
                "moat":          _avg_with_fallback([p_opm]),
                "cashflow":      _avg_with_fallback([p_netm]),
            }
            by_ticker[str(tk).zfill(6)] = g
            sec = sector or "기타"
            if sec not in sector_sums:
                sector_sums[sec] = {k: 0.0 for k in _RADAR_GROUPS}
                sector_cnt[sec] = 0
            for k in _RADAR_GROUPS:
                sector_sums[sec][k] += g[k]
            sector_cnt[sec] += 1

        by_sector = {
            sec: {k: round(sector_sums[sec][k] / sector_cnt[sec], 1) for k in _RADAR_GROUPS}
            for sec in sector_sums if sector_cnt[sec] > 0
        }
        return {"by_ticker": by_ticker, "by_sector": by_sector}

    return _cached("finance_radar_table", fetch, ttl=1800)


def get_radar(ticker: str, model_version: str = "latest") -> Optional[dict]:
    """종목의 5요인 레이더 데이터 + 동일 섹터 평균 비교.

    레이더 점수는 `finance` 테이블 기반 universe 백분위(0-100)로 산출한다.
    헤더 정보(name/score/tier/sector)는 `scores` 최신 행에서 가져온다.
    """
    ver = _resolve_version(model_version)
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        latest = _get_latest_date(ver)

        # 헤더 정보 (없어도 레이더는 반환)
        name = sector = tier = None
        score = None
        if latest:
            row = con.execute(
                """
                SELECT s.name, s.sector, s.score, s.tier
                FROM scores s
                WHERE s.model_version=? AND CAST(s.date AS VARCHAR)=? AND s.ticker=?
                """,
                [ver, latest, t],
            ).fetchone()
            if row:
                name, sector, score, tier = row

        radar_tbl = _finance_radar_table()
        groups = radar_tbl["by_ticker"].get(t)
        if groups is None:
            # 재무 데이터가 없는 종목 — 0 폴백
            groups = {g: 0.0 for g in _RADAR_GROUPS}

        # 섹터 평균: by_sector 는 stocks.wics_mid_name 으로 키가 잡혀 있으므로
        # scores.sector("IT" 등 다른 분류)가 아닌 wics_mid_name 으로 조회해야 한다.
        sector_avg = {g: 0.0 for g in _RADAR_GROUPS}
        srow = con.execute(
            "SELECT wics_mid_name FROM stocks WHERE ticker=?", [t]
        ).fetchone()
        wics_sector = srow[0] if srow else None
        if wics_sector and wics_sector in radar_tbl["by_sector"]:
            sector_avg = radar_tbl["by_sector"][wics_sector]

        return {
            "ticker":         t,
            "name":           name,
            # scores 에 sector 가 없으면 wics_mid_name 를 폴백으로 사용.
            # 이전엔 정의되지 않은 sec_key 를 참조해 미존재 ticker 호출이 NameError → 500.
            "sector":         sector or wics_sector or "",
            "score":          float(score) if score is not None else None,
            "tier":           tier,
            "model_version":  ver,
            "date":           latest,
            "groups":         groups,            # {growth:..., profitability:..., ...}
            "sector_average": sector_avg,
            "source":         "finance_percentile",
        }

    return _cached("radar", fetch, ttl=600, ticker=t, model_version=ver)

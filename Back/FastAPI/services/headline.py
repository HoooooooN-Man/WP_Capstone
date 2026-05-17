"""
services/headline.py
====================
P1-10 (PRD §8.1) — 종목 카드에 표시될 한 줄 추천 사유 자동 생성.

룰 기반 텍스트 생성 (LLM 미사용 — 비용·지연 회피):
  1. SHAP TopFactors 상위 1~2개 + 피처 그룹 → 핵심 키워드 추출
  2. tier · 점수 구간 → 강도 부사 ("강력한", "안정적인", "주목할")
  3. 섹터 정보 → 도메인 컨텍스트
  4. 템플릿 조립

예시 출력:
  - "AI 인프라 수혜 + ROE 30% 강세 → 반도체 대장주"
  - "재무 안전성 우수 + 배당 지속 → 안정적 가치주"
  - "성장률 60% + 영업이익률 개선 → 고성장 모멘텀"
"""

from __future__ import annotations

import json
from typing import Optional

from .feature_groups import classify_feature

# 그룹별 키워드 매핑 → 사용자 표시용 한국어
GROUP_DISPLAY = {
    "growth":        ("성장",      "성장률",     "고성장"),
    "profitability": ("수익성",    "마진 개선", "수익성 강세"),
    "safety":        ("안전성",    "재무 안전",  "안정적"),
    "moat":          ("독점력",    "시장 지배",  "경쟁우위"),
    "cashflow":      ("현금창출",  "현금흐름",   "현금 흑자"),
    "macro":         ("매크로",    "시장 환경",  "외부 환경"),
}


def _strength_word(score: float | None, tier: str | None) -> str:
    """점수·티어 → 강도 부사."""
    t = (tier or "").upper()
    try:
        s = float(score) if score is not None else 0
    except (TypeError, ValueError):
        s = 0
    if t == "A" and s >= 90:
        return "강력한"
    if t == "A":
        return "주목할"
    if t == "B":
        return "양호한"
    if t == "D":
        return "주의 필요"
    return "선별적"


def _top_factor_phrases(top_factors: list[dict] | None, max_n: int = 2) -> list[str]:
    """SHAP TopFactors → 핵심 키워드 2개 추출."""
    if isinstance(top_factors, str):
        try:
            top_factors = json.loads(top_factors)
        except Exception:
            return []

    if not isinstance(top_factors, list) or not top_factors:
        return []

    # SHAP 값 절댓값 기준 정렬
    items = []
    for f in top_factors:
        if not isinstance(f, dict):
            continue
        name = f.get("feature") or f.get("name") or ""
        raw = f.get("shap") if "shap" in f else f.get("value")
        sign = "+"
        try:
            val = float(raw)
            sign = "+" if val >= 0 else "-"
            abs_val = abs(val)
        except (TypeError, ValueError):
            continue
        items.append((abs_val, sign, name))
    items.sort(key=lambda x: x[0], reverse=True)

    phrases = []
    seen_groups = set()
    for _, sign, name in items[: max_n * 3]:
        group = classify_feature(name)
        if group in seen_groups or group == "macro":
            continue
        seen_groups.add(group)
        ko, key, _ = GROUP_DISPLAY.get(group, ("", "", ""))
        if not ko:
            continue
        direction = "강세" if sign == "+" else "부진"
        phrases.append(f"{key} {direction}")
        if len(phrases) >= max_n:
            break
    return phrases


def _finance_phrases(per: float | None, pbr: float | None, roe: float | None,
                     rev_growth: float | None, dividend_yield: float | None) -> list[str]:
    """B4: SHAP 부재 시 finance 지표에서 두드러진 신호 1~2개 추출."""
    phrases: list[str] = []
    # ROE 우수 → 수익성 강세
    if roe is not None and roe >= 15:
        phrases.append(f"ROE {roe:.1f}% 강세")
    # 매출 성장 → 성장성
    if rev_growth is not None and rev_growth >= 15:
        phrases.append(f"매출 성장 +{rev_growth:.0f}%")
    elif rev_growth is not None and rev_growth <= -10:
        phrases.append("매출 역성장")
    # PER 저평가 → 가치
    if per is not None and 0 < per < 10:
        phrases.append(f"PER {per:.1f}배 저평가")
    # PBR 저평가
    if pbr is not None and 0 < pbr < 1.0:
        phrases.append(f"PBR {pbr:.2f}배 자산주")
    # 배당 매력
    if dividend_yield is not None and dividend_yield >= 4.0:
        phrases.append(f"배당 {dividend_yield:.1f}%")
    return phrases[:2]


def generate_headline(
    name: str | None,
    sector: str | None,
    score: float | None,
    tier: str | None,
    top_factors: list[dict] | None,
    per: float | None = None,
    pbr: float | None = None,
    roe: float | None = None,
    rev_growth_yoy: float | None = None,
    dividend_yield: float | None = None,
) -> str:
    """카드 헤드라인 1줄 생성.

    우선순위: SHAP top_factors → finance 지표 (B4 신규) → score+tier+sector fallback.
    """
    strength = _strength_word(score, tier)
    phrases = _top_factor_phrases(top_factors, max_n=2)
    sector_part = f"{sector} 섹터" if sector else "주력 종목"

    if phrases:
        body = " + ".join(phrases)
        return f"{body} → {sector_part}의 {strength} 신호"

    # B4: SHAP 가 비어 있어도 finance 지표 기반으로 차별화된 헤드라인.
    fin_phrases = _finance_phrases(per, pbr, roe, rev_growth_yoy, dividend_yield)
    if fin_phrases:
        body = " + ".join(fin_phrases)
        return f"{body} → {sector_part}의 {strength} 종목"

    # Fallback — SHAP 없을 때 (다양성 위해 ticker+score 해시로 변형)
    try:
        s = float(score) if score is not None else None
    except (TypeError, ValueError):
        s = None

    if s is None:
        return f"{sector_part} {strength} 종목"

    # tier·점수·섹터 조합에 따른 다양한 메시지
    tier_upper = (tier or "").upper()
    if tier_upper == "A" and s >= 95:
        templates = [
            f"{sector_part} 최상위 점수 — 핵심 추천 종목",
            f"전 종목 상위권 진입 — {sector_part}의 리더",
            f"점수 {round(s, 1)} — {sector_part} 톱티어",
        ]
    elif tier_upper == "A":
        templates = [
            f"{sector_part}의 {strength} A티어 종목",
            f"점수 {round(s, 1)} — A티어 진입 기준 충족",
            f"{sector_part} 상위권 — 적극 검토 가능",
        ]
    elif tier_upper == "B":
        templates = [
            f"{sector_part} 중상위 종목 — 보유 검토",
            f"안정적인 B티어 — 분산 포트폴리오 후보",
        ]
    elif tier_upper == "D":
        templates = [
            f"{sector_part} 하위권 — 보수적 접근 권장",
            f"D티어 — 단기 모멘텀 약함",
        ]
    else:
        templates = [
            f"{sector_part} {strength} 종목 (점수 {round(s, 1)})",
            f"점수 {round(s, 1)} — 관망 또는 선별적 접근",
        ]

    # 결정적 선택 (같은 종목은 항상 같은 메시지 — 캐시 무효화 방지)
    name_hash = sum(ord(c) for c in (name or "")) if name else 0
    return templates[name_hash % len(templates)]


def attach_headlines(items: list[dict]) -> list[dict]:
    """추천/검색 결과에 headline 필드 부착 (in-place)."""
    for r in items:
        r["headline"] = generate_headline(
            name=r.get("name"),
            sector=r.get("sector"),
            score=r.get("score"),
            tier=r.get("tier"),
            top_factors=r.get("top_factors"),
            per=r.get("per"),
            pbr=r.get("pbr"),
            roe=r.get("roe"),
            rev_growth_yoy=r.get("rev_growth_yoy"),
            dividend_yield=r.get("dividend_yield"),
        )
    return items

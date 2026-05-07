"""
HTML 리포트 — 슬라이스 × 메트릭 매트릭스 한 페이지.

캡스톤 보고서 챕터 "다차원 슬라이스 평가" 의 그림 자산. 외부 의존성 없이
순수 문자열로 HTML 생성 (jinja 등 추가 의존성 회피).
"""

from __future__ import annotations

import html
from datetime import datetime, timezone


_HEAD_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       max-width: 1100px; margin: 24px auto; padding: 0 16px; color: #1f2937; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 28px 0 8px; padding-bottom: 4px;
     border-bottom: 1px solid #e5e7eb; }
.subhead { color: #6b7280; font-size: 13px; margin: 0 0 18px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { padding: 6px 10px; border-bottom: 1px solid #e5e7eb; text-align: right; }
th:first-child, td:first-child { text-align: left; }
th { background: #f9fafb; font-weight: 600; color: #374151; }
.metric-good { color: #16a34a; font-weight: 600; }
.metric-warn { color: #b45309; font-weight: 600; }
.metric-bad  { color: #dc2626; font-weight: 600; }
.note { color: #6b7280; font-style: italic; font-size: 12px; }
.footer { margin-top: 30px; font-size: 11px; color: #9ca3af; }
.kpi-box { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;
           margin: 12px 0 24px; }
.kpi { background: #f9fafb; border-left: 3px solid #2563eb; padding: 10px 12px; }
.kpi .lbl { font-size: 11px; color: #6b7280; }
.kpi .val { font-size: 18px; font-weight: 700; color: #111827; font-variant-numeric: tabular-nums; }
"""


def _fmt(v, *, pct: bool = False, digits: int = 4) -> str:
    if v is None:
        return "<span class='note'>—</span>"
    if pct:
        return f"{v * 100:.2f}%"
    return f"{v:.{digits}f}"


def _ece_class(ece: float | None) -> str:
    if ece is None: return ""
    if ece < 0.05:  return "metric-good"
    if ece < 0.10:  return "metric-warn"
    return "metric-bad"


def _sharpe_class(sr: float | None) -> str:
    if sr is None: return ""
    if sr > 1.0:   return "metric-good"
    if sr > 0.0:   return "metric-warn"
    return "metric-bad"


def _row_for_metrics(label: str, m: dict) -> str:
    return (
        f"<tr>"
        f"<td>{html.escape(label)}</td>"
        f"<td>{m.get('n_rows', 0):,}</td>"
        f"<td>{m.get('n_periods', 0)}</td>"
        f"<td>{_fmt(m.get('auc'), digits=4)}</td>"
        f"<td class='{_ece_class(m.get('ece'))}'>{_fmt(m.get('ece'), digits=4)}</td>"
        f"<td class='{_sharpe_class(m.get('sharpe'))}'>{_fmt(m.get('sharpe'), digits=2)}</td>"
        f"<td>{_fmt(m.get('mdd'), pct=True)}</td>"
        f"<td>{_fmt(m.get('alpha_cum'), pct=True)}</td>"
        f"</tr>"
    )


def _slice_table(title: str, dimension: str, slice_dicts: list[dict]) -> str:
    sub = [s for s in slice_dicts if s.get("dimension") == dimension]
    if not sub:
        return f"<h2>{html.escape(title)}</h2><p class='note'>슬라이스 결과 없음</p>"
    rows_html = "".join(_row_for_metrics(s["key"], s["metrics"]) for s in sub)
    return (
        f"<h2>{html.escape(title)}</h2>"
        f"<table>"
        f"<thead><tr>"
        f"<th>{html.escape(dimension)}</th>"
        f"<th>n_rows</th><th>n_periods</th>"
        f"<th>AUC</th><th>ECE</th><th>Sharpe</th><th>MDD</th><th>α vs KOSPI</th>"
        f"</tr></thead><tbody>{rows_html}</tbody></table>"
    )


def render_html(
    *,
    model_version: str,
    overall: dict,
    slices: list[dict],
) -> str:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n_slices = len(slices)

    kpi_html = (
        "<div class='kpi-box'>"
        f"<div class='kpi'><div class='lbl'>AUC</div><div class='val'>{_fmt(overall.get('auc'))}</div></div>"
        f"<div class='kpi'><div class='lbl'>ECE</div><div class='val'>{_fmt(overall.get('ece'))}</div></div>"
        f"<div class='kpi'><div class='lbl'>Sharpe</div><div class='val'>{_fmt(overall.get('sharpe'), digits=2)}</div></div>"
        f"<div class='kpi'><div class='lbl'>MDD</div><div class='val'>{_fmt(overall.get('mdd'), pct=True)}</div></div>"
        f"<div class='kpi'><div class='lbl'>α vs KOSPI</div><div class='val'>{_fmt(overall.get('alpha_cum'), pct=True)}</div></div>"
        "</div>"
    )

    body = (
        f"<h1>v{html.escape(model_version)} 평가 하네스 리포트</h1>"
        f"<p class='subhead'>생성 시각 {timestamp} · 슬라이스 차원 {n_slices//1}개 · "
        f"표본 {overall.get('n_rows', 0):,} 행 / {overall.get('n_periods', 0)} period</p>"
        + "<h2>전체</h2>" + kpi_html
        + _slice_table("연도별 (time)",       "time",     slices)
        + _slice_table("섹터별 (sector)",     "sector",   slices)
        + _slice_table("시총 4분위 (cap_size)", "cap_size", slices)
        + _slice_table("시장 국면 (regime)",   "regime",   slices)
        + (
            "<div class='footer'>"
            "Tier 1.2 평가 하네스 (PRD §3.5.1 / 캡스톤 §3.2). "
            "ECE 색상: <span class='metric-good'>< 0.05</span> 양호 · "
            "<span class='metric-warn'>0.05–0.10</span> 주의 · "
            "<span class='metric-bad'>≥ 0.10</span> 재캘리브레이션 검토. "
            "Sharpe 는 20거래일 period 단위 annualized (p/y=13). "
            "n_periods &lt; 3 인 슬라이스는 운용 메트릭을 *예시* 로만 해석할 것."
            "</div>"
        )
    )

    return (
        "<!doctype html><html lang='ko'><head>"
        "<meta charset='utf-8'>"
        f"<title>v{html.escape(model_version)} 평가 하네스 리포트</title>"
        f"<style>{_HEAD_CSS}</style>"
        "</head><body>"
        f"{body}"
        "</body></html>"
    )

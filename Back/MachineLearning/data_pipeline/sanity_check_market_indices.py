# -*- coding: utf-8 -*-
"""
sanity_check_market_indices.py — market_indices.kospi_close 적재 정합성 게이트
=============================================================================
배경(2026-05-25): KOSPI 2025-26 급등(2400→6600, ×2.75)이 *부패 의심* 됐으나, FinanceDataReader
`KS11`(권위 소스) 대조 결과 DB와 ×1.00 일치 — **실제 메가캡 강세장**으로 확정. 즉 *큰 변동은 정당*하며
절대 임계(월 ±15% 등)는 실데이터를 오탐한다. → 게이트는 **독립 소스 대조형**(값 불일치만 오류로 판정).

검사:
  1) [ERROR] 독립 소스(FDR KS11, 폴백 yfinance ^KS11) 대비 월말 종가 |비율−1| > TOL(기본 2%) → 적재 오류 의심
  2) [INFO ] 일변동 |>20%| → 정보성 경고만(실제일 수 있음, 차단 안 함)
  3) [WARN ] 독립 소스 미가용(네트워크/패키지) → 대조 불가, skip (gate 통과로 처리)

용례 (collect_and_build / backfill 이후):
  python sanity_check_market_indices.py --months 18         # 최근 18개월 대조
  exit code 0 = OK / 1 = 소스 불일치(적재 오류 의심) → 운영자 확인
"""
from __future__ import annotations
import argparse, sys, json
from datetime import datetime
from pathlib import Path
import pandas as pd, numpy as np

DB = Path(r"E:\Capstone Data\project_data\db\market_data.duckdb")
TOL = 0.02          # 독립 소스 대비 허용 오차(2%) — 초과 시 적재 오류 의심
DAILY_INFO = 0.20   # 일변동 정보성 경고 임계(차단 아님)


def log(m): print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


def fetch_reference(start: str, end: str):
    """독립 KOSPI 소스. FinanceDataReader KS11 우선, yfinance ^KS11 폴백. 실패 시 None."""
    try:
        import FinanceDataReader as fdr
        s = fdr.DataReader("KS11", start, end)["Close"].rename("ref")
        return s, "FinanceDataReader KS11"
    except Exception as e:
        log(f"  FDR 불가: {type(e).__name__}")
    try:
        import yfinance as yf
        h = yf.Ticker("^KS11").history(start=start, end=end)["Close"].rename("ref")
        h.index = h.index.tz_localize(None)
        return (h, "yfinance ^KS11") if len(h) else (None, None)
    except Exception as e:
        log(f"  yfinance 불가: {type(e).__name__}")
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=18, help="대조 최근 개월수")
    ap.add_argument("--tol", type=float, default=TOL)
    a = ap.parse_args()
    import duckdb
    con = duckdb.connect(str(DB), read_only=True)
    db = con.execute("SELECT date, kospi_close FROM market_indices WHERE kospi_close IS NOT NULL ORDER BY date").fetchdf()
    con.close()
    db["date"] = pd.to_datetime(db["date"]); db = db.set_index("date")["kospi_close"]
    end = db.index.max(); start = (end - pd.DateOffset(months=a.months))
    win = db[db.index >= start]

    errors, infos = [], []
    # 2) 일변동 정보성
    dr = win.pct_change().dropna()
    for d, v in dr[abs(dr) > DAILY_INFO].items():
        infos.append(f"일변동 {d.date()} {100*v:+.1f}% (정보성 — 실제일 수 있음)")

    # 1) 독립 소스 대조
    ref, src = fetch_reference(start.strftime("%Y-%m-%d"), (end + pd.Timedelta(days=2)).strftime("%Y-%m-%d"))
    status = "OK"
    cmp_rows = []
    if ref is None:
        log("  [WARN] 독립 소스 미가용 → 대조 skip (gate 통과 처리)")
        status = "SKIP_NO_SOURCE"
    else:
        log(f"  대조 소스: {src}")
        dme = win.resample("ME").last().dropna()
        rme = ref.resample("ME").last().dropna()
        # 부분(진행 중) 트레일링 월 제외 — DB 말일이 월말보다 5일 이상 이르면 미완료 월로 보고 비교 제외(staleness 오탐 방지)
        maxd = win.index.max(); me_of_max = maxd + pd.offsets.MonthEnd(0)
        if (me_of_max - maxd).days > 5:
            dme = dme[dme.index < me_of_max]
            infos.append(f"트레일링 부분월 {me_of_max.strftime('%Y-%m')} 비교 제외(DB 말일 {maxd.date()}, staleness)")
        for d in dme.index:
            rv = rme.reindex([d], method="nearest", tolerance=pd.Timedelta("6D")).dropna()
            if not len(rv): continue
            r = float(rv.iloc[0]); s = float(dme.loc[d]); ratio = s / r if r else float("nan")
            cmp_rows.append({"month": d.strftime("%Y-%m"), "db": round(s, 1), "ref": round(r, 1), "ratio": round(ratio, 4)})
            if abs(ratio - 1) > a.tol:
                errors.append(f"{d.strftime('%Y-%m')}: DB {s:.1f} vs {src} {r:.1f} (×{ratio:.3f}, |Δ|>{a.tol:.0%}) — 적재 오류 의심")
        status = "FAIL_SOURCE_MISMATCH" if errors else "OK"

    out = {"checked_at": datetime.now().isoformat(timespec="seconds"), "window_months": a.months,
           "db_range": [str(win.index.min().date()), str(win.index.max().date())],
           "reference": src, "tol": a.tol, "status": status,
           "errors": errors, "infos": infos, "monthly_compare": cmp_rows}
    rep = Path(__file__).resolve().parent / "sanity_check_market_indices.json"
    json.dump(out, open(rep, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    log(f"[{status}] errors={len(errors)} infos={len(infos)} → {rep.name}")
    for e in errors: log(f"  ✗ {e}")
    for i in infos[:5]: log(f"  · {i}")
    # 게이트: 소스 불일치만 실패(exit 1). 큰 변동(info)·소스 미가용(skip)은 통과.
    sys.exit(1 if status == "FAIL_SOURCE_MISMATCH" else 0)


if __name__ == "__main__":
    main()

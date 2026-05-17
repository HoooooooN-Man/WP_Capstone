"""
cohort_backtest.py
==================
User_Scenarios.md 의 "장기 사용 시나리오" 근거 산출용 — 코호트별/리밸런싱
수익률을 `market_data.duckdb` 의 실데이터로 백테스트한다.

방법:
  - 진입일(rec_date)별로 scores 전 종목을 가져와 코호트 필터/정렬에 필요한
    파생 지표를 붙인다:
      volatility_60d, ret_lag_60d  ← prices 60거래일
      per, pbr, dividend_yield     ← finance (base_date <= rec_date 최신)
  - services.personalization.rerank_for_cohort 를 그대로 적용해 코호트별 Top-5 선정.
  - 종료일(가장 최근 거래일) 종가까지 보유했을 때의 평균 수익률 산출.
  - 리밸런싱: 동일 코호트를 (a) 매수 후 보유, (b) 월 1회 재선정 비교.

실행: cd Back && python -X utf8 -m FastAPI.scripts.cohort_backtest
"""
from __future__ import annotations

import os
import statistics
from pathlib import Path

import duckdb

from FastAPI.services.personalization import rerank_for_cohort

DB_PATH = os.getenv("DUCKDB_PATH", r"E:\Capstone Data\project_data\db\market_data.duckdb")
COHORTS = ["balanced", "conservative", "growth", "dividend", "value"]
TOP_K = 5


def _to_int(d: str) -> int:
    return int(d.replace("-", ""))


def load_universe(con, ver: str) -> dict[str, list[str]]:
    """거래일 목록 (오름차순)."""
    rows = con.execute(
        "SELECT DISTINCT CAST(date AS VARCHAR) d FROM scores WHERE model_version=? ORDER BY d",
        [ver],
    ).fetchall()
    return [r[0] for r in rows]


def enriched_rows(con, ver: str, rec_date: str) -> list[dict]:
    """rec_date 의 scores + 코호트 필터용 파생 지표."""
    rec_int = _to_int(rec_date)

    base = con.execute(
        """
        SELECT DISTINCT s.ticker, ROUND(CAST(s.score AS DOUBLE),1) AS score, s.close
        FROM scores s
        WHERE s.model_version=? AND CAST(s.date AS VARCHAR)=?
        """,
        [ver, rec_date],
    ).fetchall()
    rows = {t: {"ticker": t, "score": sc, "close": cl} for t, sc, cl in base if cl}

    if not rows:
        return []
    tickers = list(rows)
    ph = ",".join(["?"] * len(tickers))

    # 가격 파생: 직전 61 거래일로 volatility_60d, ret_lag_60d
    px = con.execute(
        f"""
        WITH w AS (
            SELECT ticker, date, close,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
            FROM prices
            WHERE ticker IN ({ph}) AND date <= ?
        )
        SELECT ticker, date, close FROM w WHERE rn <= 61 ORDER BY ticker, date
        """,
        tickers + [rec_int],
    ).fetchall()
    series: dict[str, list[float]] = {}
    for t, _d, c in px:
        series.setdefault(t, []).append(float(c))
    for t, seq in series.items():
        if len(seq) >= 2:
            rets = [(seq[i] - seq[i - 1]) / seq[i - 1] for i in range(1, len(seq)) if seq[i - 1]]
            rows[t]["volatility_60d"] = statistics.pstdev(rets) if len(rets) > 1 else None
            rows[t]["ret_lag_60d"] = (seq[-1] - seq[0]) / seq[0] if seq[0] else None

    # 재무: base_date <= rec_date 최신 분기
    fin = con.execute(
        f"""
        WITH w AS (
            SELECT ticker, per, pbr, dividend_yield, base_date,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY base_date DESC) rn
            FROM finance
            WHERE ticker IN ({ph}) AND base_date <= ?
        )
        SELECT ticker, per, pbr, dividend_yield FROM w WHERE rn = 1
        """,
        tickers + [float(rec_int)],
    ).fetchall()
    for t, per, pbr, dy in fin:
        if t in rows:
            rows[t]["per"] = per
            rows[t]["pbr"] = pbr
            # finance.dividend_yield 는 % 단위(예: 2.42) → personalization 은 비율(0.02) 기대
            rows[t]["dividend_yield"] = (float(dy) / 100.0) if dy is not None else None

    # score DESC, ticker ASC 로 정렬 — 동점(score=100 다수) 시 결정적 tie-break.
    # rerank 가 정렬키를 안 바꾸는 코호트(balanced/필터형)는 이 순서를 그대로 사용.
    return sorted(rows.values(), key=lambda r: (-(r.get("score") or 0.0), r["ticker"]))


def latest_close_map(con, tickers: list[str]) -> dict[str, float]:
    ph = ",".join(["?"] * len(tickers))
    rows = con.execute(
        f"""
        SELECT ticker, close FROM (
            SELECT ticker, close, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
            FROM prices WHERE ticker IN ({ph})
        ) WHERE rn = 1
        """,
        tickers,
    ).fetchall()
    return {t: float(c) for t, c in rows if c}


def avg_return(picks: list[dict], latest: dict[str, float]) -> float | None:
    rets = []
    for p in picks:
        rc, lc = p.get("close"), latest.get(p["ticker"])
        if rc and lc:
            rets.append((lc - rc) / rc * 100)
    return round(statistics.mean(rets), 2) if rets else None


def main() -> None:
    con = duckdb.connect(DB_PATH, read_only=True)
    ver = con.execute(
        "SELECT model_version FROM scores ORDER BY inserted_at DESC LIMIT 1"
    ).fetchone()[0]
    dates = load_universe(con, ver)
    end_date = dates[-1]
    print(f"model_version={ver}  기간={dates[0]} ~ {end_date}  거래일수={len(dates)}\n")

    # 진입일 후보 (월초 근처)
    entries = [dates[0], dates[len(dates) // 3], dates[2 * len(dates) // 3]]

    # ── 1) 코호트별 buy&hold 수익률 (진입일 → 종료일) ─────────────────────────
    print("=== 코호트별 Top-5 매수 후 보유 수익률 (%) ===")
    print(f"{'진입일':<12}" + "".join(f"{c:>14}" for c in COHORTS))
    all_tickers = set()
    cohort_curves: dict[str, list[float]] = {c: [] for c in COHORTS}
    for ed in entries:
        rows = enriched_rows(con, ver, ed)
        line = f"{ed:<12}"
        for c in COHORTS:
            picks = rerank_for_cohort(rows, c, top_k=TOP_K)
            all_tickers.update(p["ticker"] for p in picks)
            line += f"{'':>14}"  # placeholder, 채움은 아래
        print(line.rstrip())
    latest = latest_close_map(con, list(all_tickers) or ["005930"])

    for ed in entries:
        rows = enriched_rows(con, ver, ed)
        line = f"{ed:<12}"
        for c in COHORTS:
            picks = rerank_for_cohort(rows, c, top_k=TOP_K)
            r = avg_return(picks, latest)
            cohort_curves[c].append(r if r is not None else 0.0)
            line += f"{(f'{r:+.2f}' if r is not None else 'n/a'):>14}"
        print(line)
    print()
    print(f"{'평균':<12}" + "".join(
        f"{statistics.mean(cohort_curves[c]):>+14.2f}" for c in COHORTS))

    # ── 2) 리밸런싱 효과: balanced 코호트 ────────────────────────────────────
    print("\n=== 리밸런싱 효과 (balanced 코호트, 진입일 " + entries[0] + " ~ " + end_date + ") ===")
    # (a) buy & hold
    rows0 = enriched_rows(con, ver, entries[0])
    bh = rerank_for_cohort(rows0, "balanced", top_k=TOP_K)
    bh_ret = avg_return(bh, latest)
    print(f"  (a) 매수 후 보유          : {bh_ret:+.2f}%")

    # (b) 월 1회 재선정 — 각 구간 수익률을 복리 연결
    seg_dates = entries + [end_date]
    compound = 1.0
    seg_log = []
    for i in range(len(seg_dates) - 1):
        d0, d1 = seg_dates[i], seg_dates[i + 1]
        rows_i = enriched_rows(con, ver, d0)
        picks_i = rerank_for_cohort(rows_i, "balanced", top_k=TOP_K)
        # d1 종가맵
        tk = [p["ticker"] for p in picks_i]
        ph = ",".join(["?"] * len(tk))
        d1_close = dict(con.execute(
            f"""SELECT ticker, close FROM (
                   SELECT ticker, close, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                   FROM prices WHERE ticker IN ({ph}) AND date <= ?
               ) WHERE rn=1""",
            tk + [_to_int(d1)],
        ).fetchall())
        seg_rets = [(float(d1_close[p["ticker"]]) - p["close"]) / p["close"]
                    for p in picks_i if p["ticker"] in d1_close and p["close"]]
        seg = statistics.mean(seg_rets) if seg_rets else 0.0
        compound *= (1 + seg)
        seg_log.append((d0, d1, seg * 100))
    rebal_ret = (compound - 1) * 100
    for d0, d1, s in seg_log:
        print(f"      {d0} → {d1}: {s:+.2f}%")
    print(f"  (b) 월 1회 재선정 (복리)  : {rebal_ret:+.2f}%")
    print(f"  → 리밸런싱 효과          : {rebal_ret - bh_ret:+.2f}%p")


if __name__ == "__main__":
    main()

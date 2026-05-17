"""
services/diversify.py
=====================
W3 — MMR (Maximal Marginal Relevance) 다양성 후처리.

설계 원칙:
  - 모델 재학습 0. 서빙 *후처리* — score 정렬 결과를 sim 거리로 reranking.
  - **`diversify=None` 또는 `"none"` → no-op**. 기존 동작 유지 (CLAUDE.md §반드시 지킬 것 2번).
  - 입력 컬럼·sim 매트릭스 누락 시 graceful no-op.

3 sim 모드:
  - `sector`      : 같은 sector 거리 0, 다른 sector 거리 1 (binary).
                    rows 에 이미 sector 컬럼이 있어 *DB 의존 0*. W3.5E sector_proximity
                    FAIL (ratio 0.989) 로 추천 안 함, 옵션으로만 노출.
  - `correlation` : 60d 수익률 시계열 상관 → 거리 = 1 - corr.
                    W3.5E correlation_alignment PASS — **권장 활성 모드**.
  - `embedding`   : ticker_embeddings (PG) 또는 emb_v1.pt 의 64dim 벡터 코사인 거리.
                    W3.5E embedding_rank PASS, but W5 ablation 에서 ndcg@10 −0.041 negative gain.
                    옵션으로만 노출. 67 features baseline 위 재검증 후 default 전환 검토.

MMR 알고리즘:
  - Greedy. 첫 선택 = score 최고.
  - 이후: argmax_t [λ · score(t) − (1−λ) · max_s∈selected sim(t, s)]
  - λ ∈ [0,1]. λ=1 → score 만, λ=0 → 다양성 만.

본 모듈의 *MMR 자체* 는 순수 함수 — 단위 테스트 가능. sim provider 만 외부 의존.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable, Optional

import numpy as np


VALID_DIVERSIFY = frozenset({"none", "sector", "correlation", "embedding"})
DEFAULT_LAMBDA = 0.7   # score 70% / diversity 30%


def normalize_diversify(diversify: Optional[str]) -> str:
    """입력값 정규화. 알 수 없는 모드는 'none' (no-op) 반환."""
    if not diversify:
        return "none"
    d = str(diversify).strip().lower()
    if d in VALID_DIVERSIFY:
        return d
    return "none"


# ── MMR 순수 함수 ───────────────────────────────────────────────────────────

def mmr_rerank(
    rows:       list[dict],
    sim:        Callable[[str, str], float],   # (ticker_a, ticker_b) → 거리 ∈ [0, ?]
    *,
    score_key:  str   = "score",
    ticker_key: str   = "ticker",
    lambda_:    float = DEFAULT_LAMBDA,
    top_k:      int   = 20,
) -> list[dict]:
    """
    MMR greedy. score·sim 함수 의존성 주입.

    Notes
    -----
    - sim 은 *거리* (가까울수록 0). 우리 정의: distance = 1 − cosine_or_corr.
    - λ ∈ [0,1]. CLAUDE.md "diversify=none 시 기존 동작" — 호출자가 mode 별 처리.
    - top_k=0 또는 len(rows)≤1 → 그대로 반환.
    """
    if top_k <= 0 or len(rows) <= 1:
        return list(rows)
    if not (0.0 <= lambda_ <= 1.0):
        raise ValueError(f"lambda_ 는 [0, 1] 범위: {lambda_}")

    # score 정규화 — λ score 와 (1−λ) sim 이 비교 가능하도록 [0, 1] 로.
    scores = np.array([float(r.get(score_key, 0.0)) for r in rows], dtype=float)
    if scores.max() > scores.min():
        norm_scores = (scores - scores.min()) / (scores.max() - scores.min())
    else:
        norm_scores = np.zeros_like(scores)

    n        = len(rows)
    selected: list[int] = []
    remaining = set(range(n))

    # 1) 첫 선택 — score 최고.
    first = int(np.argmax(norm_scores))
    selected.append(first)
    remaining.discard(first)

    # 2) 이후 — MMR.
    while remaining and len(selected) < top_k:
        best_idx   = -1
        best_value = -np.inf
        for i in remaining:
            ti = rows[i][ticker_key]
            # max sim *거리* — 거리가 클수록 다양함. MMR 는 -max_distance 로 다양성 보상.
            # 하지만 우리는 *작은 거리 = 비슷함* 이므로 max_distance ↑ ⇒ 다양성 ↑.
            # 표준 MMR (similarity 기반) 식을 거리로 옮기면:
            #   value = λ score + (1−λ) min_sim_distance(i, selected)
            # → 가까운 종목이 많이 선택돼있으면 이 후보의 *최소 거리* 가 작음 → penalize.
            min_dist = min(float(sim(ti, rows[s][ticker_key])) for s in selected)
            value = lambda_ * float(norm_scores[i]) + (1.0 - lambda_) * min_dist
            if value > best_value:
                best_value = value
                best_idx   = i
        if best_idx == -1:
            break
        selected.append(best_idx)
        remaining.discard(best_idx)

    return [rows[i] for i in selected]


# ── sim providers ──────────────────────────────────────────────────────────

def make_sector_sim(rows: list[dict], sector_key: str = "sector") -> Callable[[str, str], float]:
    """rows 의 ticker → sector 매핑. 같은 sector 거리 0, 다른 거리 1.
    매핑 없거나 None 인 ticker 는 거리 1 로 가정 (다양성 보상)."""
    by_ticker: dict[str, Optional[str]] = {r["ticker"]: r.get(sector_key) for r in rows}

    def sim(a: str, b: str) -> float:
        sa, sb = by_ticker.get(a), by_ticker.get(b)
        if sa is None or sb is None:
            return 1.0
        return 0.0 if sa == sb else 1.0
    return sim


def make_correlation_sim(
    tickers:    list[str],
    *,
    duckdb_path: str,
    period_days: int = 60,
) -> Callable[[str, str], float]:
    """
    DuckDB prices 에서 *최근 period_days 영업일* 의 종가 log-return 상관 계산.
    한 번에 전체 매트릭스 계산 후 closure 로 lookup. *tickers 가 작은 경우* (≤500) 만 적합.
    거리 = 1 − corr. corr 결측 시 거리 1 (다양성 보상 — 데이터 없는 페어는 다른 종목으로 봄).
    """
    import duckdb

    if len(tickers) < 2:
        return lambda a, b: 0.0

    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        date_max = con.execute("SELECT MAX(date) FROM prices").fetchone()[0]
        if date_max is None:
            return lambda a, b: 1.0
        # B14 fix: 이전 `int(date_max) - period_days * 100` 은 YYYYMMDD 정수 산술이라
        # 월 경계에서 잘못된 날짜(예: 20194901) 가 나옴. 실제 날짜로 환산 후 다시 INTEGER.
        from datetime import datetime as _dt, timedelta as _td
        d_max = _dt.strptime(str(int(date_max)), "%Y%m%d")
        # 영업일 ≈ 달력일 × 1.4 (주말 흡수) — 안전 마진 포함.
        d_cut = d_max - _td(days=int(period_days * 1.5))
        cutoff = int(d_cut.strftime("%Y%m%d"))
        tlist = ",".join(f"'{t}'" for t in tickers)
        df = con.execute(f"""
            SELECT date, ticker, close
            FROM prices
            WHERE ticker IN ({tlist}) AND date >= {cutoff}
            ORDER BY ticker, date
        """).fetchdf()
    finally:
        con.close()

    if df.empty:
        return lambda a, b: 1.0

    # ticker별 log return 시계열 (길이 통일).
    returns: dict[str, np.ndarray] = {}
    for t, g in df.groupby("ticker"):
        g = g.sort_values("date")
        if len(g) < 10:
            continue
        close = g["close"].values.astype(float)
        ret   = np.diff(np.log(np.where(close > 0, close, 1e-6)))
        returns[t] = ret[-period_days:]

    # 매트릭스 (sparse dict).
    # zero-variance 시계열 페어는 corrcoef 결과가 NaN + numpy 가 stderr 에
    # "RuntimeWarning: invalid value encountered in divide" 를 매번 찍어 운영 로그
    # 가 도배된다. np.errstate 로 해당 RuntimeWarning 만 억제하고, 후처리에서
    # np.isfinite 로 NaN→0.0 폴백.
    corr_mat: dict[tuple[str, str], float] = {}
    keys = list(returns.keys())
    with np.errstate(invalid="ignore", divide="ignore"):
        for i, a in enumerate(keys):
            ra = returns[a]
            ra_std = float(np.std(ra[-len(ra):])) if len(ra) else 0.0
            for b in keys[i:]:
                rb = returns[b]
                n = min(len(ra), len(rb))
                if n < 10:
                    continue
                # 분산 0 인 시계열은 corrcoef 가 정의 안 됨 — 즉시 0 으로 폴백.
                rb_std = float(np.std(rb[-n:]))
                if ra_std == 0.0 or rb_std == 0.0:
                    c = 0.0
                else:
                    c = float(np.corrcoef(ra[-n:], rb[-n:])[0, 1])
                    if not np.isfinite(c):
                        c = 0.0
                corr_mat[(a, b)] = c
                corr_mat[(b, a)] = c

    def sim(a: str, b: str) -> float:
        if a == b:
            return 0.0
        c = corr_mat.get((a, b))
        if c is None:
            return 1.0      # 모르는 페어 — 다양성 보상
        return float(max(0.0, 1.0 - c))    # corr < 0 도 거리 1 (음의 상관도 다른 행동).

    return sim


def make_embedding_sim(
    tickers: list[str],
    *,
    pg_url:          Optional[str] = None,
    checkpoint_path: Optional[str] = None,
    duckdb_path:     Optional[str] = None,
) -> Callable[[str, str], float]:
    """
    ticker → 64dim 벡터. PG ticker_embeddings 우선, 비어있거나 실패면 emb_v1.pt 즉석 추출.
    거리 = 1 − cosine. 결측 ticker 는 거리 1.

    **W5 ablation 후행** — 임베딩이 ndcg@10 −0.041 (v11a→v11b) negative gain.
    MMR 다양성에서의 가치는 ranking gain 과 *독립* 이지만 default 아님.
    """
    pg_url   = pg_url or os.getenv("EVENTS_PG_URL",
                                   "postgresql://postgres:postgres@localhost:5432/wp_capstone")
    rows: Optional[list[tuple[str, list[float]]]] = None
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(pg_url, future=True)
        with engine.connect() as conn:
            rows = [(r[0], list(r[1])) for r in conn.execute(
                text("SELECT ticker, vector FROM ticker_embeddings")
            ).all()]
    except Exception:
        rows = None

    if not rows:
        # checkpoint fallback — train_lambdarank_v11.attach_embeddings 패턴.
        if checkpoint_path is None or duckdb_path is None:
            return lambda a, b: 1.0     # 데이터 없음 — graceful no-op
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "MachineLearning"))
            from extract_embeddings import extract_all, load_model_from_checkpoint  # type: ignore
            model, _, _ = load_model_from_checkpoint(Path(checkpoint_path))
            extracted = extract_all(model, Path(duckdb_path), max_tickers=0)
            rows = [(t, list(v)) for (t, v, *_) in extracted]
        except Exception:
            return lambda a, b: 1.0

    by_ticker: dict[str, np.ndarray] = {}
    for t, v in rows:
        arr = np.asarray(v, dtype=np.float32)
        n = float(np.linalg.norm(arr))
        by_ticker[t] = arr / n if n > 0 else arr

    def sim(a: str, b: str) -> float:
        if a == b:
            return 0.0
        va, vb = by_ticker.get(a), by_ticker.get(b)
        if va is None or vb is None:
            return 1.0
        c = float(np.dot(va, vb))
        c = max(-1.0, min(1.0, c))
        return 1.0 - c

    return sim

"""
run_sanity_check.py
===================
W3.5E 진입점 — emb_v1 sanity check 4종 실행 후 박제.

흐름:
  1. PG `ticker_embeddings` 에서 (ticker, vector) 로드 (또는 --from-checkpoint 시 즉석 추출).
  2. DuckDB `scores` 에서 ticker → sector 매핑.
  3. DuckDB `prices` 에서 시계열 수익률 상관 계산 (샘플 기간).
  4. 계열사 그룹 매핑 (단순 prefix 룰 + 알려진 그룹 하드코딩).
  5. 4 sanity check 실행 → JSON 박제.

박제 위치: `_archive/embeddings_v1/sanity_check.json`
  → CLAUDE.md §3 hard gate. n_passed ≥ 2 이면 W3·W5·W8 진입 가능.

사용:
  py run_sanity_check.py                                  # PG 에서 임베딩 로드
  py run_sanity_check.py --from-checkpoint <path>         # 즉석 추출
  py run_sanity_check.py --max-tickers 100                # 일부만
  py run_sanity_check.py --dry-run                        # 박제 생략
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DUCKDB_PATH   = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
# 차차기 W3 — version 기반 동적 박제 디렉터리. embeddings_v1 봉인 유지, emb_v2+ 별도.
_ARCHIVE_ROOT = Path(r"E:\Capstone Data\_archive")

PG_URL = os.getenv(
    "EVENTS_PG_URL",
    "postgresql://postgres:postgres@localhost:5432/wp_capstone",
)


# 알려진 계열사 그룹 — 명세 §sanity check #3 기준 (삼성·LG·SK·현대 등). 대표 종목만.
KNOWN_CHAEBOL_GROUPS: dict[str, str] = {
    # 삼성
    "005930": "samsung", "005935": "samsung", "010140": "samsung",
    "028260": "samsung", "032830": "samsung", "207940": "samsung",
    "009150": "samsung", "018260": "samsung", "029780": "samsung",
    # LG
    "066570": "lg",      "003550": "lg",      "051910": "lg",
    "032640": "lg",      "034220": "lg",      "108860": "lg",
    "373220": "lg",      "001120": "lg",
    # SK
    "000660": "sk",      "034730": "sk",      "017670": "sk",
    "096770": "sk",      "326030": "sk",      "402340": "sk",
    "285130": "sk",      "011790": "sk",
    # 현대
    "005380": "hyundai", "005385": "hyundai", "012330": "hyundai",
    "086280": "hyundai", "001450": "hyundai", "267260": "hyundai",
    "010620": "hyundai", "011200": "hyundai",
    # 한화
    "000880": "hanwha",  "009830": "hanwha",  "272210": "hanwha",
    "377300": "hanwha",
    # 롯데
    "004990": "lotte",   "023530": "lotte",   "071840": "lotte",
    "005300": "lotte",
    # GS
    "078930": "gs",      "001250": "gs",      "006360": "gs",
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 데이터 로딩 ─────────────────────────────────────────────────────────────

def load_embeddings_from_pg(max_tickers: int = 0):
    from sqlalchemy import create_engine, text
    engine = create_engine(PG_URL, future=True)
    with engine.connect() as conn:
        sql = "SELECT ticker, vector FROM ticker_embeddings ORDER BY ticker"
        if max_tickers > 0:
            sql += f" LIMIT {int(max_tickers)}"
        rows = conn.execute(text(sql)).all()
    if not rows:
        return [], np.zeros((0, 0), dtype=np.float32)
    tickers = [r[0] for r in rows]
    vectors = np.array([r[1] for r in rows], dtype=np.float32)
    return tickers, vectors


def load_embeddings_from_checkpoint(checkpoint_path: Path, max_tickers: int):
    """PG 가 비어있을 때의 fallback — 즉석 추출."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_embeddings import extract_all, load_model_from_checkpoint

    model, version, _ = load_model_from_checkpoint(checkpoint_path)
    rows = extract_all(model, DUCKDB_PATH, max_tickers=max_tickers)
    tickers = [r[0] for r in rows]
    vectors = np.array([r[1] for r in rows], dtype=np.float32)
    return tickers, vectors, version


def load_sector_map(tickers: list[str]) -> dict[str, str]:
    import duckdb
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        if not tickers:
            return {}
        tlist = ",".join(f"'{t}'" for t in tickers)
        rows = con.execute(f"""
            SELECT ticker, MAX(sector) AS sector
            FROM scores
            WHERE ticker IN ({tlist})
            GROUP BY ticker
        """).fetchall()
        return {t: s for t, s in rows if s}
    finally:
        con.close()


def compute_correlation_pairs(
    tickers:    list[str],
    *,
    # n=60 sample 에서 high(>=0.67) pair 0개 발견 → 200 으로 확장. 19,900 pair 산출.
    n_sample:   int = 200,
    period_days: int = 252,
    rng:        Optional[np.random.Generator] = None,
) -> dict[tuple[str, str], float]:
    """
    *최근 period_days 영업일* 의 종가 수익률 상관. 모든 쌍이 아닌
    무작위 샘플 n_sample × n_sample 매트릭스만 계산 (O(N²) 회피).
    """
    import duckdb
    rng = rng or np.random.default_rng(2)
    if len(tickers) < 5:
        return {}

    sample_size = min(n_sample, len(tickers))
    sample = list(rng.choice(tickers, size=sample_size, replace=False))

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        date_max = con.execute("SELECT MAX(date) FROM prices").fetchone()[0]
        if date_max is None:
            return {}
        # YYYYMMDD BIGINT → 대략 period_days 거래일 전.
        cutoff = int(date_max) - period_days * 100   # 단순 cutoff (거래일 정확도 X)

        tlist = ",".join(f"'{t}'" for t in sample)
        df = con.execute(f"""
            SELECT date, ticker, close
            FROM prices
            WHERE ticker IN ({tlist}) AND date >= {cutoff}
            ORDER BY ticker, date
        """).fetchdf()
    finally:
        con.close()

    if df.empty:
        return {}

    # ticker 별 close → returns
    returns_by_ticker: dict[str, np.ndarray] = {}
    by_t = df.groupby("ticker")
    common_dates: Optional[set] = None
    for t, g in by_t:
        g = g.sort_values("date")
        if len(g) < 30:
            continue
        close = g["close"].values.astype(float)
        ret = np.diff(np.log(np.where(close > 0, close, 1e-6)))
        # 마지막 N일만 사용해 길이 통일 시도 (정확한 계산은 join 필요).
        returns_by_ticker[t] = ret[-period_days:]

    out: dict[tuple[str, str], float] = {}
    keys = list(returns_by_ticker.keys())
    for i, a in enumerate(keys):
        ra = returns_by_ticker[a]
        for b in keys[i + 1 :]:
            rb = returns_by_ticker[b]
            n = min(len(ra), len(rb))
            if n < 30:
                continue
            corr = float(np.corrcoef(ra[-n:], rb[-n:])[0, 1])
            if not np.isfinite(corr):
                continue
            out[(a, b)] = corr
    return out


# ── 메인 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="W3.5E — sanity check 4종 실행·박제")
    parser.add_argument("--from-checkpoint", default=None,
                        help="PG 비어있을 때 fallback. emb_v1.pt 경로.")
    parser.add_argument("--max-tickers", type=int, default=0,
                        help="0 = 전체. 빠른 시연 50.")
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--force",       action="store_true",
                        help="기존 박제 덮어쓰기.")
    parser.add_argument("--version",     default="emb_v1")
    args = parser.parse_args()

    log("=== run_sanity_check (W3.5E) ===")
    log(f"  DuckDB: {DUCKDB_PATH}")

    # 1. 임베딩 로딩.
    version = args.version
    if args.from_checkpoint:
        log(f"  loading from checkpoint: {args.from_checkpoint}")
        tickers, vectors, version = load_embeddings_from_checkpoint(
            Path(args.from_checkpoint), args.max_tickers,
        )
    else:
        log(f"  loading from PG: {PG_URL}")
        try:
            tickers, vectors = load_embeddings_from_pg(args.max_tickers)
        except Exception as e:
            log(f"[ERROR] PG 로드 실패: {e}")
            log("  --from-checkpoint <path> 로 직접 추출 가능.")
            return 1

    if len(tickers) == 0:
        log("[ERROR] 임베딩 0개. extract_embeddings.py 먼저 실행 또는 --from-checkpoint.")
        return 2
    log(f"  embeddings: {len(tickers)} × {vectors.shape[1]}")

    # 2. 섹터 매핑.
    log("  loading sector map …")
    sectors = load_sector_map(tickers)
    log(f"    matched {len(sectors)}/{len(tickers)}")

    # 3. 시계열 상관 (샘플).
    log("  computing return correlation pairs (sampled) …")
    correlation = compute_correlation_pairs(tickers, n_sample=min(200, len(tickers)))
    log(f"    pairs computed: {len(correlation)}")

    # 4. 계열사 그룹.
    groups = {t: KNOWN_CHAEBOL_GROUPS[t] for t in tickers if t in KNOWN_CHAEBOL_GROUPS}
    log(f"  chaebol groups matched: {len(groups)} tickers")

    # 5. 4 sanity 실행.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from embeddings.sanity import run_all_sanity

    payload = run_all_sanity(
        embeddings=vectors,
        tickers=tickers,
        sectors=sectors or None,
        correlation=correlation or None,
        groups=groups or None,
        pass_min=2,
    )
    payload["embedding_version"] = version
    payload["computed_at"]       = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload["n_tickers"]         = len(tickers)
    payload["embedding_dim"]     = int(vectors.shape[1]) if vectors.size else 0

    log("=== Sanity result ===")
    log(f"  n_passed = {payload['n_passed']} / {payload['n_checks_run']} "
        f"(threshold {payload['pass_threshold']})")
    log(f"  overall_pass = {payload['overall_pass']}")
    for c in payload["checks"]:
        mark = "PASS" if c["passed"] else "FAIL"
        log(f"    [{mark}] {c['name']}")

    # 6. 박제.
    if args.dry_run:
        log("--- dry-run (no write) ---")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    # 차차기 W3 — version 기반 디렉터리 (embeddings_v1 봉인, emb_v2+ 별도).
    # version="emb_v2" → "embeddings_v2".
    short = version.replace("emb_", "") if version.startswith("emb_") else version
    archive_dir = _ARCHIVE_ROOT / f"embeddings_{short}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    out_path = archive_dir / "sanity_check.json"
    if out_path.exists() and not args.force:
        log(f"[REFUSED] 이미 박제: {out_path}. --force 명시 시 덮어쓰기.")
        return 3
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  wrote {out_path}")
    return 0 if payload["overall_pass"] else 4    # exit≠0 으로 hard gate 신호


if __name__ == "__main__":
    sys.exit(main())

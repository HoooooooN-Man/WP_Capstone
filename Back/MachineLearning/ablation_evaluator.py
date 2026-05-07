"""
ablation_evaluator.py
=====================
Tier 1B 4.2 (PRD §5.5 / 캡스톤 §4.2) — 단일 LightGBM vs 3-모델 메타 스태킹 비교.

목적:
  - v9 의 메타 스태킹(LGBM+XGB+Cat → meta logistic + isotonic) 이 단일 LGBM 대비
    *얼마나* 더 나은지 정량 측정.
  - 차이가 크면 앙상블 정당화, 차이가 미미하면 단일 모델로 단순화 검토.
  - 보고서 챕터 "앙상블의 가치" 의 직접 자산.

설계:
  - DB 의 `scores` 테이블에 이미 prob_lgbm / prob_xgb / prob_cat / prob_ensemble 4종이
    적재되어 있다 (precompute_scores.py 가 적재).
  - holdout 동일 분할 (2026 Q1·Q2) 의 forward-evaluable 행만 사용.
  - 각 prob 시리즈에 대해 AUC + ECE + Brier 산출 → ablation_v9.json 박제.

사용:
  cd Back/MachineLearning
  python ablation_evaluator.py
  python ablation_evaluator.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np

from calibration_metrics import expected_calibration_error, brier_score
from sklearn.metrics import roc_auc_score


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DB_PATH = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
ARCHIVE_DIR = Path(r"E:\Capstone Data\_archive\holdout_2026_q1_q2")

MODEL_VERSION = "v9"
LABEL_THRESHOLD = 0.05
FORWARD_DAYS = 20


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_eval_rows(con: duckdb.DuckDBPyConnection):
    """forward 20거래일 라벨 부착된 행. holdout_evaluator 와 동일 정책."""
    df = con.execute("""
        SELECT
            CAST(s.date AS VARCHAR)                          AS date_str,
            CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT) AS date_int,
            s.ticker,
            CAST(s.prob_lgbm     AS DOUBLE) AS prob_lgbm,
            CAST(s.prob_xgb      AS DOUBLE) AS prob_xgb,
            CAST(s.prob_cat      AS DOUBLE) AS prob_cat,
            CAST(s.prob_ensemble AS DOUBLE) AS prob_ensemble,
            CAST(p.close         AS DOUBLE) AS close_today
        FROM scores s
        JOIN prices p
          ON p.ticker = s.ticker
         AND p.date   = CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT)
        WHERE s.model_version = ?
        ORDER BY s.ticker, s.date
    """, [MODEL_VERSION]).fetchdf()
    df = df.sort_values(["ticker", "date_int"]).reset_index(drop=True)
    df["close_fwd"] = df.groupby("ticker")["close_today"].shift(-FORWARD_DAYS)
    df = df.dropna(subset=["close_fwd"]).copy()
    df["fwd_return"] = (df["close_fwd"] - df["close_today"]) / df["close_today"]
    df["label"] = (df["fwd_return"] >= LABEL_THRESHOLD).astype(int)
    return df


def evaluate_prob(name: str, y_true, y_prob) -> dict:
    """단일 prob 시리즈에 대한 AUC·ECE·Brier."""
    return {
        "name":  name,
        "n":     int(len(y_true)),
        "auc":   round(float(roc_auc_score(y_true, y_prob)), 4),
        "ece":   round(float(expected_calibration_error(y_true, y_prob, n_bins=10)), 4),
        "brier": round(float(brier_score(y_true, y_prob)), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true",
                        help="박제 덮어쓰기 (errata 추가 시에만)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DB_PATH}")
        return 1

    log("=== Ablation: single LGBM vs ensemble (Tier 1B 4.2) ===")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = load_eval_rows(con)
    finally:
        con.close()
    log(f"  Eval rows (forward-{FORWARD_DAYS}d labeled): {len(df):,}")
    log(f"  Buy-rate: {df['label'].mean():.4f}")

    y = df["label"].values
    results = [
        evaluate_prob("lgbm_alone",     y, df["prob_lgbm"].values),
        evaluate_prob("xgb_alone",      y, df["prob_xgb"].values),
        evaluate_prob("cat_alone",      y, df["prob_cat"].values),
        evaluate_prob("ensemble_meta_isotonic", y, df["prob_ensemble"].values),
        # 단순 평균 앙상블 (baseline) — meta-stacking 의 부가가치 측정용.
        evaluate_prob(
            "ensemble_simple_mean",
            y,
            np.mean(df[["prob_lgbm", "prob_xgb", "prob_cat"]].values, axis=1),
        ),
    ]

    # 앙상블 vs LGBM Δ.
    lgbm   = next(r for r in results if r["name"] == "lgbm_alone")
    ens    = next(r for r in results if r["name"] == "ensemble_meta_isotonic")
    delta  = {
        "delta_auc":   round(ens["auc"]   - lgbm["auc"],   4),
        "delta_ece":   round(ens["ece"]   - lgbm["ece"],   4),
        "delta_brier": round(ens["brier"] - lgbm["brier"], 4),
        "interpretation": _interpret(ens, lgbm),
    }

    payload = {
        "schema_version": "1.0",
        "generated_at":   datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version":  MODEL_VERSION,
        "n_observations": int(len(df)),
        "label_threshold": LABEL_THRESHOLD,
        "forward_days":   FORWARD_DAYS,
        "candidates":     results,
        "ensemble_vs_lgbm": delta,
        "policy": (
            "AUC 차이가 +0.005 이내이면 앙상블 부가가치 미미 → 단일 LGBM 단순화 검토 "
            "(PRD §5.5). 그 외에는 앙상블 유지가 합리적."
        ),
    }

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARCHIVE_DIR / "ablation_v9.json"
    if out_path.exists() and not args.force:
        log(f"[REFUSED] 이미 박제됨: {out_path}")
        log("  --force 명시 시에만 덮어쓰기.")
        return 2
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  Wrote {out_path}")

    # 사람이 읽는 요약.
    md_path = ARCHIVE_DIR / "ablation_v9_summary.md"
    md = _build_summary_md(payload)
    md_path.write_text(md, encoding="utf-8")
    log(f"  Wrote {md_path}")

    return 0


def _interpret(ens: dict, lgbm: dict) -> str:
    d_auc = ens["auc"] - lgbm["auc"]
    if abs(d_auc) < 0.005:
        return ("앙상블 부가가치 미미 — 단일 LGBM 단순화 검토 가능 "
                f"(ΔAUC={d_auc:+.4f})")
    if d_auc > 0:
        return ("앙상블이 단일 LGBM 대비 분류 성능 우월 "
                f"(ΔAUC={d_auc:+.4f}, ΔECE={ens['ece']-lgbm['ece']:+.4f})")
    return ("단일 LGBM 이 앙상블 대비 우월 — 앙상블 재검토 권고 "
            f"(ΔAUC={d_auc:+.4f})")


def _build_summary_md(p: dict) -> str:
    lines = [
        f"# v9 Ablation 요약 — 단일 LGBM vs 메타 스태킹",
        f"",
        f"- **봉인 시각**: {p['generated_at']}",
        f"- **표본**: {p['n_observations']:,} 행 (holdout 2026 Q1·Q2, forward-{p['forward_days']}d)",
        f"- **라벨 임계**: ≥+{int(p['label_threshold']*100)}%",
        f"",
        f"## 후보별 분류 성능",
        f"",
        f"| 모델 | AUC | ECE | Brier |",
        f"|------|-----|-----|-------|",
    ]
    for r in p["candidates"]:
        lines.append(f"| {r['name']} | {r['auc']} | {r['ece']} | {r['brier']} |")
    d = p["ensemble_vs_lgbm"]
    lines += [
        f"",
        f"## 앙상블 − LGBM 단독",
        f"",
        f"- ΔAUC   = **{d['delta_auc']:+.4f}**",
        f"- ΔECE   = {d['delta_ece']:+.4f} (음수면 캘리브레이션 개선)",
        f"- ΔBrier = {d['delta_brier']:+.4f} (음수면 개선)",
        f"",
        f"**해석**: {d['interpretation']}",
        f"",
        f"## 정책 (PRD §5.5)",
        f"",
        f"{p['policy']}",
        f"",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())

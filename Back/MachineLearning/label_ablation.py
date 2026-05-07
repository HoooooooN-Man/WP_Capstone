"""
label_ablation.py
=================
Tier 1B 4.3 (PRD §5.1 / 캡스톤 §4.3) — 단순 이진 라벨 vs Triple Barrier 라벨 비교.

캡스톤 축약 정책:
  - v11 신규 학습 *하지 않음* (캡스톤 §9 함정).
  - 대신 *기존 v9 prob_lgbm 의 ranking 능력*이 라벨 정의에 따라 어떻게 변하는지
    측정. 두 라벨에 대해 동일한 prob 시리즈로 AUC·ECE 산출.
  - 차이가 크면 "차기 모델은 TB 라벨로 학습 시 더 큰 신호 가능" 권고.
  - 차이가 작으면 "현재 라벨이 적절함" 검증.

산출:
  - _archive/holdout_2026_q1_q2/ablation_label_v9.json
  - _archive/holdout_2026_q1_q2/ablation_label_v9_summary.md
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
import pandas as pd
from sklearn.metrics import roc_auc_score

from calibration_metrics import expected_calibration_error, brier_score
from triple_barrier import TripleBarrierParams, label_series


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DB_PATH = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
ARCHIVE_DIR = Path(r"E:\Capstone Data\_archive\holdout_2026_q1_q2")

MODEL_VERSION = "v9"
SIMPLE_THRESHOLD = 0.05
HORIZON = 20


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_holdout_with_prices(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """holdout 행 + 향후 horizon+10 거래일치 가격."""
    df = con.execute("""
        SELECT
            s.ticker,
            CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT) AS date_int,
            CAST(s.prob_lgbm     AS DOUBLE) AS prob_lgbm,
            CAST(s.prob_ensemble AS DOUBLE) AS prob_ensemble
        FROM scores s
        WHERE s.model_version = ?
        ORDER BY s.ticker, s.date
    """, [MODEL_VERSION]).fetchdf()
    return df


def load_full_prices(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """라벨 산출용 — holdout 기간 + horizon 만큼의 prices."""
    return con.execute("""
        SELECT ticker, date AS date_int, CAST(close AS DOUBLE) AS close
        FROM prices
        ORDER BY ticker, date
    """).fetchdf()


def attach_labels(holdout: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """ticker 별로 가격 시계열 → 두 라벨 모두 부착."""
    out_rows = []
    tb_params = TripleBarrierParams(upper_pct=0.07, lower_pct=0.04, horizon=HORIZON)

    for ticker, ph in prices.groupby("ticker"):
        ph = ph.sort_values("date_int").reset_index(drop=True)
        close_arr = ph["close"].values
        # 두 라벨 모두 산출.
        tb = label_series(close_arr, tb_params)
        # simple binary 직접: t+horizon 일 후 ≥ +5%.
        n = len(close_arr)
        sb = np.full(n, -1, dtype=np.int8)
        for t in range(n - HORIZON):
            if close_arr[t] <= 0:
                continue
            ret = (close_arr[t + HORIZON] - close_arr[t]) / close_arr[t]
            sb[t] = 1 if ret >= SIMPLE_THRESHOLD else 0

        ph["label_tb"]     = tb
        ph["label_simple"] = sb
        out_rows.append(ph[["ticker", "date_int", "label_tb", "label_simple"]])

    labels_df = pd.concat(out_rows, ignore_index=True)
    merged = holdout.merge(labels_df, on=["ticker", "date_int"], how="inner")
    # 두 라벨 모두 산출 가능한 행만 사용.
    merged = merged[(merged["label_tb"] != -1) & (merged["label_simple"] != -1)].copy()
    return merged


def evaluate(name: str, y_true, y_prob) -> dict:
    return {
        "label":  name,
        "n":      int(len(y_true)),
        "buy_rate": round(float(y_true.mean()), 4),
        "auc":    round(float(roc_auc_score(y_true, y_prob)), 4),
        "ece":    round(float(expected_calibration_error(y_true, y_prob, n_bins=10)), 4),
        "brier":  round(float(brier_score(y_true, y_prob)), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DB_PATH}")
        return 1

    log("=== Label Ablation (Tier 1B 4.3) ===")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        holdout = load_holdout_with_prices(con)
        prices  = load_full_prices(con)
    finally:
        con.close()
    log(f"  holdout rows: {len(holdout):,}  | prices rows: {len(prices):,}")

    log("Computing labels (Triple Barrier + simple binary) per ticker …")
    df = attach_labels(holdout, prices)
    log(f"  Both labels resolvable: {len(df):,}")

    if df.empty:
        log("[ERROR] 라벨 부착 실패 (forward 데이터 부족).")
        return 2

    log("Comparing v9 prob_lgbm under each label definition …")
    res_simple = evaluate("simple_binary_5pct", df["label_simple"].values, df["prob_lgbm"].values)
    res_tb     = evaluate("triple_barrier",     df["label_tb"].values,     df["prob_lgbm"].values)
    res_ens_simple = evaluate("simple_binary_5pct (vs prob_ensemble)",
                              df["label_simple"].values, df["prob_ensemble"].values)
    res_ens_tb     = evaluate("triple_barrier (vs prob_ensemble)",
                              df["label_tb"].values,     df["prob_ensemble"].values)

    delta = {
        "delta_auc_lgbm":   round(res_tb["auc"] - res_simple["auc"], 4),
        "delta_ece_lgbm":   round(res_tb["ece"] - res_simple["ece"], 4),
        "delta_buy_rate":   round(res_tb["buy_rate"] - res_simple["buy_rate"], 4),
    }

    interpretation = _interpret(delta["delta_auc_lgbm"])

    payload = {
        "schema_version": "1.0",
        "generated_at":   datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version":  MODEL_VERSION,
        "n_observations": int(len(df)),
        "horizon_trading_days": HORIZON,
        "simple_label": {
            "definition": f"forward {HORIZON}-day return ≥ +{int(SIMPLE_THRESHOLD*100)}%",
        },
        "triple_barrier_label": {
            "upper_pct": 0.07,
            "lower_pct": 0.04,
            "horizon":   HORIZON,
            "tie_break_at_expiry": "terminal sign",
            "reference":  "López de Prado (2018), Advances in Financial Machine Learning",
        },
        "results": {
            "v9_prob_lgbm": {
                "vs_simple": res_simple,
                "vs_triple_barrier": res_tb,
            },
            "v9_prob_ensemble": {
                "vs_simple": res_ens_simple,
                "vs_triple_barrier": res_ens_tb,
            },
        },
        "delta_under_label_change": delta,
        "interpretation": interpretation,
        "next_cycle_recommendation": _recommend(delta["delta_auc_lgbm"]),
    }

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARCHIVE_DIR / "ablation_label_v9.json"
    if out_path.exists() and not args.force:
        log(f"[REFUSED] 이미 박제됨: {out_path}")
        return 2
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  Wrote {out_path}")

    md_path = ARCHIVE_DIR / "ablation_label_v9_summary.md"
    md_path.write_text(_build_summary(payload), encoding="utf-8")
    log(f"  Wrote {md_path}")
    return 0


def _interpret(delta_auc: float) -> str:
    if abs(delta_auc) < 0.005:
        return ("두 라벨 정의 모두 v9 prob_lgbm 의 ranking 능력 차이 미미 — "
                f"현재 단순 이진 라벨이 캡스톤 범위에서는 적절 (ΔAUC={delta_auc:+.4f})")
    if delta_auc > 0:
        return ("Triple Barrier 라벨에서 v9 prob_lgbm 이 더 잘 적합 — "
                f"차기 모델 학습 시 TB 라벨 검토 권고 (ΔAUC={delta_auc:+.4f})")
    return ("단순 이진 라벨에서 v9 prob_lgbm 의 ranking 능력이 더 강함 — "
            f"v9 의 학습 라벨이 모델 적합도와 일치 (ΔAUC={delta_auc:+.4f})")


def _recommend(delta_auc: float) -> str:
    if abs(delta_auc) < 0.005:
        return "차기 사이클(v11) 라벨 결정 시: 단순 이진 vs TB 둘 다 시도 후 OOS 우월 채택."
    if delta_auc > 0.01:
        return ("차기 사이클(v11) — Triple Barrier 라벨로 LGBM 재학습 우선 검토. "
                "단, holdout 분리 정책 (PRD §3.5.3) 그대로 유지.")
    return "차기 사이클 — 단순 이진 라벨 유지가 합리적."


def _build_summary(p: dict) -> str:
    sb = p["results"]["v9_prob_lgbm"]["vs_simple"]
    tb = p["results"]["v9_prob_lgbm"]["vs_triple_barrier"]
    sb_e = p["results"]["v9_prob_ensemble"]["vs_simple"]
    tb_e = p["results"]["v9_prob_ensemble"]["vs_triple_barrier"]
    return (
        f"# v9 Label Ablation 요약 — Simple vs Triple Barrier\n\n"
        f"- **봉인 시각**: {p['generated_at']}\n"
        f"- **표본**: {p['n_observations']:,} 행 (두 라벨 모두 산출 가능)\n"
        f"- **참고문헌**: {p['triple_barrier_label']['reference']}\n\n"
        f"## 라벨 정의\n\n"
        f"| 라벨 | 정의 |\n"
        f"|------|------|\n"
        f"| Simple Binary | t+{p['horizon_trading_days']}일 수익률 ≥ +5% |\n"
        f"| Triple Barrier | 상단 +7% / 하단 −4% / 만료 {p['horizon_trading_days']}일 — 첫 닿은 barrier |\n\n"
        f"## v9 prob_lgbm 의 분류 성능\n\n"
        f"| 라벨 | 매수율 | AUC | ECE | Brier |\n"
        f"|------|--------|-----|-----|-------|\n"
        f"| Simple +5% | {sb['buy_rate']} | **{sb['auc']}** | {sb['ece']} | {sb['brier']} |\n"
        f"| Triple Barrier | {tb['buy_rate']} | **{tb['auc']}** | {tb['ece']} | {tb['brier']} |\n\n"
        f"## v9 prob_ensemble 의 분류 성능 (참고)\n\n"
        f"| 라벨 | AUC | ECE | Brier |\n"
        f"|------|-----|-----|-------|\n"
        f"| Simple +5% | {sb_e['auc']} | {sb_e['ece']} | {sb_e['brier']} |\n"
        f"| Triple Barrier | {tb_e['auc']} | {tb_e['ece']} | {tb_e['brier']} |\n\n"
        f"## 결과\n\n"
        f"- **ΔAUC (TB − Simple, prob_lgbm)** = {p['delta_under_label_change']['delta_auc_lgbm']:+.4f}\n"
        f"- **Δ매수율** = {p['delta_under_label_change']['delta_buy_rate']:+.4f}\n\n"
        f"**해석**: {p['interpretation']}\n\n"
        f"**차기 사이클 권고**: {p['next_cycle_recommendation']}\n\n"
        f"## 캡스톤 한계 명시\n\n"
        f"본 ablation 은 *기존 v9 prob_lgbm 을 두 라벨로 재평가*한 결과로, "
        f"라벨 정의 변경 후 *재학습한 v11 모델*의 성능 차이는 **추정 외**다. "
        f"v11 신규 학습은 캡스톤 범위 외 (캡스톤 §9 함정·v11 본격 학습 금지) — "
        f"PRD v1.2 §5.6 v11 승격 절차에 따라 차기 사이클에서 진행한다.\n"
    )


if __name__ == "__main__":
    sys.exit(main())

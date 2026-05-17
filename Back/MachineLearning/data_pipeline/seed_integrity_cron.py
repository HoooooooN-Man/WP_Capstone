"""
seed_integrity_cron.py
======================
KRX 종목 명단 vs seed.csv 정합성 점검 cron.

목적:
  - KOSPI/KOSDAQ 신규 상장 / 상장 폐지 종목 자동 감지.
  - seed.csv 누락 종목 = 모든 downstream pipeline 미수집 → KB금융/삼성물산
    같은 케이스 (2026-05-17) 재발 방지.

흐름:
  1. pykrx 로 KOSPI + KOSDAQ 현재 종목 명단 조회.
  2. seed.csv 와 diff.
  3. 누락 종목 (KRX 에 있는데 seed 에 없음) → 콘솔 + cron_runs.detail JSON 박제.
  4. 상장폐지 종목 (seed 에 있는데 KRX 에 없음) → 동일 박제.
  5. cron_telemetry 통해 silent-fail 정책 준수.

사용:
  py seed_integrity_cron.py                  # 점검 + 텔레메트리
  py seed_integrity_cron.py --dry-run        # 텔레메트리 없이 콘솔만
  py seed_integrity_cron.py --auto-add       # 누락 종목 seed.csv 자동 추가 (보수: dry-run 권장)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Windows 콘솔 UTF-8 강제 (한글 박스출력 회피).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
try:
    from cron_telemetry import track_run as _track_run
except ImportError:
    @contextlib.contextmanager
    def _track_run(_step: str):
        class _H: rows = None; detail = None
        yield _H()


SEED_PATH = Path(os.getenv(
    "SEED_CSV",
    r"E:\Capstone Data\project_data\preprocessing\seed.csv",
))


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_seed() -> set[str]:
    import pandas as pd
    if not SEED_PATH.exists():
        return set()
    df = pd.read_csv(SEED_PATH, dtype={"ticker": str})
    return set(df["ticker"].str.zfill(6))


def fetch_krx_tickers() -> tuple[set[str], dict[str, str]]:
    """KOSPI + KOSDAQ 현재 종목 명단. pykrx 우선, 실패 시 KRX 공식 CSV (정적) 폴백.
    반환: (ticker_set, ticker->name).
    """
    out: set[str] = set()
    names: dict[str, str] = {}

    # 1) pykrx 시도 (Windows + 일부 네트워크에서 KRX 차단 빈번)
    try:
        from pykrx import stock
        for market in ("KOSPI", "KOSDAQ"):
            try:
                tickers = stock.get_market_ticker_list(market=market)
                if not tickers:
                    raise RuntimeError(f"{market} empty result")
                for t in tickers:
                    t6 = str(t).zfill(6)
                    out.add(t6)
                    try:
                        names[t6] = stock.get_market_ticker_name(t)
                    except Exception:
                        names[t6] = ""
            except Exception as e:
                log(f"  [WARN] pykrx {market}: {e}")
    except ImportError:
        log("  [WARN] pykrx 미설치")

    # 2) pykrx 가 빈 결과면 KRX KIND HTML 종목코드 다운로드 폴백.
    if not out:
        try:
            import pandas as pd
            url = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
            tables = pd.read_html(url, encoding="euc-kr")
            if tables:
                df = tables[0]
                if "종목코드" in df.columns and "회사명" in df.columns:
                    for _, r in df.iterrows():
                        code = str(r["종목코드"]).zfill(6)
                        out.add(code)
                        names[code] = str(r["회사명"])
                    log(f"  [폴백 OK] KRX KIND 에서 {len(out)} 종목 수집")
        except Exception as e:
            log(f"  [WARN] KRX KIND HTML 폴백 실패: {e}")

    return out, names


def main() -> int:
    parser = argparse.ArgumentParser(description="KRX vs seed.csv 정합 점검")
    parser.add_argument("--dry-run", action="store_true", help="cron_runs 박제 안 함")
    parser.add_argument("--auto-add", action="store_true",
                        help="누락 종목 seed.csv 자동 추가 (WICS 정보 없이 기본값).")
    args = parser.parse_args()

    log("=== seed_integrity ===")

    seed_tickers = load_seed()
    log(f"  seed.csv: {len(seed_tickers)} tickers")

    krx_tickers, krx_names = fetch_krx_tickers()
    log(f"  KRX (KOSPI+KOSDAQ): {len(krx_tickers)} tickers")
    if not krx_tickers:
        log("  [ERROR] KRX 조회 결과 비어있음 -pykrx 일시 오류 가능. 종료.")
        return 1

    missing = sorted(krx_tickers - seed_tickers)  # seed 누락
    delisted = sorted(seed_tickers - krx_tickers)  # seed 만 있고 KRX 없음 (상장폐지 후보)

    log(f"\n  [누락] KRX 에 있는데 seed.csv 에 없음: {len(missing)} 종목")
    for t in missing[:20]:
        log(f"    - {t} {krx_names.get(t, '')}")
    if len(missing) > 20:
        log(f"    ... (외 {len(missing) - 20} 종목)")

    log(f"\n  [상장폐지 후보] seed 에 있는데 KRX 에 없음: {len(delisted)} 종목")
    for t in delisted[:10]:
        log(f"    - {t}")
    if len(delisted) > 10:
        log(f"    ... (외 {len(delisted) - 10} 종목)")

    detail = {
        "seed_count":    len(seed_tickers),
        "krx_count":     len(krx_tickers),
        "missing_count": len(missing),
        "delisted_count": len(delisted),
        "missing_sample":  [{"ticker": t, "name": krx_names.get(t, "")} for t in missing[:20]],
        "delisted_sample": delisted[:10],
    }

    # auto-add: seed.csv 보강 (기본값 -WICS 미지정, 추후 수동 보강 필요)
    if args.auto_add and missing:
        import pandas as pd
        df = pd.read_csv(SEED_PATH, dtype={"ticker": str})
        df["ticker"] = df["ticker"].str.zfill(6)
        new_rows = []
        for t in missing:
            # 시장 추정 -KRX 조회 시 분리 했어야 정확. 임시: 6자리코드 첫자리 추정 불가 → KOSPI 기본
            new_rows.append({
                "exchange": "KOSPI", "ticker": t,
                "name": krx_names.get(t, ""),
                "wics_large": None, "wics_mid": None,
                "wics_large_name": None, "wics_mid_name": None,
            })
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True).sort_values("ticker").reset_index(drop=True)
        df.to_csv(SEED_PATH, index=False, encoding="utf-8")
        log(f"\n  [auto-add] seed.csv 에 {len(new_rows)} 종목 추가 (WICS 미지정 -수동 보강 필요)")
        detail["auto_added"] = len(new_rows)

    if args.dry_run:
        log("\n[dry-run] cron_runs 박제 생략.")
        return 0

    with _track_run("seed_integrity") as ctx:
        ctx.rows = len(missing) + len(delisted)
        ctx.detail = detail

    log(f"\n완료. missing={len(missing)} delisted={len(delisted)}")
    return 0 if len(missing) == 0 else 1  # exit code 1 = 누락 발견 (외부 모니터링 ping 용)


if __name__ == "__main__":
    sys.exit(main())

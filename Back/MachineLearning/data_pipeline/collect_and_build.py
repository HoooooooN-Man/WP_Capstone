"""
신규 데이터 수집 + 기술지표 피처 엔지니어링
----------------------------------------------
수집 전략:
  - KRX 로그인:  일별 OHLCV (MDCSTAT01501), PER/PBR (MDCSTAT03501)
  - yfinance:    KOSPI(^KS11), KOSDAQ(^KQ11), FX(USDKRW=X)
  - 수급피처:    외국인/기관 순매수, 공매도 비율 → KRX 미제공 계정이므로
                 과거 데이터 rolling mean 으로 forward-fill
수집 범위:  DuckDB prices 최신일+1 ~ 오늘 (또는 --start/--end)
출력:
  data_pipeline/raw_ohlcv.parquet        -- 신규 OHLCV
  data_pipeline/raw_index_fx.parquet     -- 신규 지수+FX
  data_pipeline/new_features.parquet     -- 모든 피처 (inference 준비 완료)

사용법:
  python collect_and_build.py
  python collect_and_build.py --start 2026-01-02 --end 2026-04-04
  python collect_and_build.py --no-collect       # 기존 raw_ohlcv 로 피처만 재빌드
"""

import os, sys, time, argparse, warnings
import numpy as np
import pandas as pd
import requests
import duckdb
from pathlib import Path
from datetime import datetime, timedelta, date

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
warnings.filterwarnings("ignore")

# ─── 경로 설정 ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(r"e:\Capstone Data")
PREP_DIR  = BASE_DIR / "project_data" / "preprocessing"
PIPE_DIR  = BASE_DIR / "data_pipeline"
DUCKDB    = BASE_DIR / "project_data" / "db" / "market_data.duckdb"
SEED_FILE = PREP_DIR / "seed.csv"
PIPE_DIR.mkdir(parents=True, exist_ok=True)

# ─── KRX 세션 ────────────────────────────────────────────────────────────────
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
_HEADERS = {
    "User-Agent"      : _UA,
    "Referer"         : "https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd",
    "X-Requested-With": "XMLHttpRequest",
}
_LOGIN_PAGE = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001.cmd"
_LOGIN_JSP  = "https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp?site=mdc"
_LOGIN_URL  = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001D1.cmd"
_DATA_URL   = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

session = requests.Session()


def login_krx(login_id: str, login_pw: str) -> bool:
    session.get(_LOGIN_PAGE, headers={"User-Agent": _UA}, timeout=15)
    session.get(_LOGIN_JSP,  headers={"User-Agent": _UA, "Referer": _LOGIN_PAGE}, timeout=15)
    payload = {"mbrNm": "", "telNo": "", "di": "", "certType": "",
                "mbrId": login_id, "pw": login_pw}
    resp = session.post(_LOGIN_URL, data=payload,
                        headers={**_HEADERS, "Referer": _LOGIN_PAGE}, timeout=15)
    ec = resp.json().get("_error_code", "")
    if ec == "CD011":
        payload["skipDup"] = "Y"
        resp = session.post(_LOGIN_URL, data=payload,
                            headers={**_HEADERS, "Referer": _LOGIN_PAGE}, timeout=15)
        ec = resp.json().get("_error_code", "")
    ok = ec == "CD001"
    print("KRX login OK" if ok else f"KRX login FAIL (code={ec})")
    return ok


def krx_get(bld: str, extra: dict, key: str = "OutBlock_1", retry: int = 3) -> list:
    params = {"bld": bld, **extra}
    for attempt in range(retry):
        try:
            resp = session.post(_DATA_URL, headers=_HEADERS, data=params, timeout=20)
            if resp.status_code != 200 or not resp.text.strip():
                time.sleep(1)
                continue
            raw = resp.text.strip()
            if raw.startswith("<"):
                return []  # HTML (blocked)
            j = resp.json()
            rows = j.get(key, j.get("output", j.get("OutBlock_1", [])))
            return rows if isinstance(rows, list) else []
        except Exception as e:
            if attempt == retry - 1:
                print(f"  KRX API error ({bld}): {e}")
            time.sleep(1 * (attempt + 1))
    return []


def safe_float(val) -> float:
    try:
        v = str(val).replace(",", "").strip()
        return float(v) if v not in ["-", "", "N/A", "nan"] else np.nan
    except:
        return np.nan


# ═══════════════════════════════════════════════════════════════════════════════
#  1. KRX - 일별 OHLCV
# ═══════════════════════════════════════════════════════════════════════════════
def fetch_ohlcv_day(trd_dd: str) -> pd.DataFrame:
    dfs = []
    for mkt_id in ["STK", "KSQ"]:
        rows = krx_get("dbms/MDC/STAT/standard/MDCSTAT01501",
                       {"mktId": mkt_id, "trdDd": trd_dd},
                       key="OutBlock_1")
        if not rows:
            continue
        df = pd.DataFrame(rows)
        col_map = {
            "ISU_SRT_CD": "ticker", "ISU_ABBRV": "name",
            "TDD_OPNPRC": "open",   "TDD_HGPRC": "high",
            "TDD_LWPRC":  "low",    "TDD_CLSPRC": "close",
            "ACC_TRDVOL": "volume", "ACC_TRDVAL": "amount",
            "MKTCAP":     "market_cap",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        df["market"] = mkt_id
        df["date"]   = trd_dd
        dfs.append(df)
        time.sleep(0.25)
    if not dfs:
        return pd.DataFrame()

    result = pd.concat(dfs, ignore_index=True)
    for c in ["open", "high", "low", "close", "volume", "amount", "market_cap"]:
        if c in result.columns:
            result[c] = result[c].apply(safe_float)

    # 유효 가격 확인 (close != NaN 인 종목만)
    result = result[result["close"].notna() & result["ticker"].str.match(r"^\d{6}$", na=False)]
    if result.empty:
        return pd.DataFrame()

    result["date"] = pd.to_datetime(result["date"], format="%Y%m%d")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  2. yfinance - KOSPI / KOSDAQ / FX
# ═══════════════════════════════════════════════════════════════════════════════
def fetch_index_fx(start_str: str, end_str: str) -> pd.DataFrame:
    """
    ^KS11(KOSPI), ^KQ11(KOSDAQ), USDKRW=X 수집
    """
    try:
        import yfinance as yf
    except ImportError:
        print("  yfinance not installed. pip install yfinance")
        return pd.DataFrame()

    symbols = {
        "^KS11"    : "kospi_close",
        "^KQ11"    : "kosdaq_close",
        "USDKRW=X" : "fx_usdkrw",
    }

    dfs = {}
    for sym, col in symbols.items():
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(start=start_str, end=end_str, auto_adjust=True)
            if hist.empty:
                print(f"  yfinance {sym}: empty")
                continue
            hist.index = hist.index.tz_localize(None)
            dfs[col] = hist["Close"].rename(col)
        except Exception as e:
            print(f"  yfinance {sym}: {e}")

    if not dfs:
        return pd.DataFrame()

    result = pd.concat(dfs.values(), axis=1).reset_index()
    result.columns = ["date"] + list(result.columns[1:])
    result["date"] = pd.to_datetime(result["date"]).dt.date.astype(str)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  3. KRX - PER/PBR (분기 스냅샷 - 필요 시)
# ═══════════════════════════════════════════════════════════════════════════════
def fetch_per_quarter(quarter_date: str) -> pd.DataFrame:
    """분기 말일 전후 탐색하여 PER/PBR 데이터 수집"""
    dt = datetime.strptime(quarter_date, "%Y%m%d")
    for i in range(10):
        d = (dt - timedelta(days=i)).strftime("%Y%m%d")
        dfs = []
        for mkt_id in ["STK", "KSQ"]:
            rows = krx_get("dbms/MDC/STAT/standard/MDCSTAT03501",
                           {"mktId": mkt_id, "trdDd": d},
                           key="output")
            if rows:
                df = pd.DataFrame(rows)
                dfs.append(df)
            time.sleep(0.2)
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            if "EPS" in combined.columns and (combined["EPS"] != "-").any():
                return d, combined
    return None, pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
#  수집 메인
# ═══════════════════════════════════════════════════════════════════════════════
def collect_all(start_krx: str, end_krx: str, seed_tickers: set):
    trading_days = [d.strftime("%Y%m%d")
                    for d in pd.bdate_range(start=start_krx, end=end_krx, freq="B")]
    print(f"\nCollecting {len(trading_days)} trading days ({start_krx} ~ {end_krx})\n")

    ohlcv_list = []
    for i, trd_dd in enumerate(trading_days, 1):
        print(f"[{i:3d}/{len(trading_days)}] {trd_dd}", end="  ")
        df = fetch_ohlcv_day(trd_dd)
        if df.empty:
            print("holiday/no data")
            continue
        df = df[df["ticker"].isin(seed_tickers)]
        ohlcv_list.append(df)
        print(f"OHLCV: {len(df)} stocks")
        time.sleep(0.25)

    if not ohlcv_list:
        return pd.DataFrame()

    df_ohlcv = pd.concat(ohlcv_list, ignore_index=True)
    df_ohlcv.to_parquet(PIPE_DIR / "raw_ohlcv.parquet", index=False)
    print(f"\nSaved raw_ohlcv.parquet: {len(df_ohlcv):,} rows")

    # yfinance index + FX
    start_yf = pd.to_datetime(start_krx).strftime("%Y-%m-%d")
    end_yf   = (pd.to_datetime(end_krx) + timedelta(days=1)).strftime("%Y-%m-%d")
    print("\nFetching index + FX via yfinance...")
    df_idx = fetch_index_fx(start_yf, end_yf)
    if not df_idx.empty:
        df_idx.to_parquet(PIPE_DIR / "raw_index_fx.parquet", index=False)
        print(f"Saved raw_index_fx.parquet: {len(df_idx)} rows")
    else:
        print("  WARNING: No index/FX data from yfinance")

    return df_ohlcv


# ═══════════════════════════════════════════════════════════════════════════════
#  기술지표 계산
# ═══════════════════════════════════════════════════════════════════════════════
def compute_technical(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["ticker", "date"]).copy()

    def calc(g: pd.DataFrame) -> pd.DataFrame:
        c  = g["close"].values.astype(float)
        v  = g["volume"].fillna(0).values.astype(float)
        hi = g["high"].values.astype(float)
        lo = g["low"].values.astype(float)
        op = g["open"].values.astype(float)
        n  = len(c)

        def rolling_mean(arr, w):
            result = np.full(n, np.nan)
            for i in range(n):
                start = max(0, i - w + 1)
                vals  = arr[start:i+1]
                valid = vals[~np.isnan(vals)]
                if len(valid) > 0:
                    result[i] = np.mean(valid)
            return result

        def rolling_std(arr, w):
            result = np.full(n, np.nan)
            for i in range(n):
                start = max(0, i - w + 1)
                vals  = arr[start:i+1]
                valid = vals[~np.isnan(vals)]
                if len(valid) >= 2:
                    result[i] = np.std(valid, ddof=1)
            return result

        def ewm_mean(arr, span):
            alpha  = 2 / (span + 1)
            result = np.full(n, np.nan)
            for i in range(n):
                if np.isnan(arr[i]):
                    continue
                if np.isnan(result[i-1]) if i > 0 else True:
                    result[i] = arr[i]
                else:
                    result[i] = alpha * arr[i] + (1 - alpha) * result[i-1]
            return result

        sma5   = rolling_mean(c, 5)
        sma20  = rolling_mean(c, 20)
        sma60  = rolling_mean(c, 60)
        ema12  = ewm_mean(c, 12)
        ema26  = ewm_mean(c, 26)

        g = g.copy()
        g["SMA_5"]  = sma5
        g["SMA_20"] = sma20
        g["SMA_60"] = sma60
        g["EMA_12"] = ema12
        g["EMA_26"] = ema26

        # Returns
        c_s  = pd.Series(c)
        g["return_1d"]  = c_s.pct_change(1).values
        g["return_5d"]  = c_s.pct_change(5).values
        g["return_20d"] = c_s.pct_change(20).values

        # Disparity
        g["Disparity_5"]  = np.where(sma5  > 0, (c / sma5  - 1) * 100, np.nan)
        g["Disparity_20"] = np.where(sma20 > 0, (c / sma20 - 1) * 100, np.nan)
        g["Disparity_60"] = np.where(sma60 > 0, (c / sma60 - 1) * 100, np.nan)

        # RSI 14
        delta = np.diff(c, prepend=c[0])
        gain  = np.where(delta > 0, delta, 0.0)
        loss  = np.where(delta < 0, -delta, 0.0)
        ag    = rolling_mean(gain, 14)
        al    = rolling_mean(loss, 14)
        rs    = np.where(al > 0, ag / al, 100)
        g["RSI_14"] = 100 - 100 / (1 + rs)

        # MACD
        macd           = ema12 - ema26
        macd_signal    = ewm_mean(macd, 9)
        g["MACD"]           = macd
        g["MACD_signal"]    = macd_signal
        g["MACD_histogram"] = macd - macd_signal

        # Stochastic
        low14  = pd.Series(lo).rolling(14, min_periods=1).min().values
        high14 = pd.Series(hi).rolling(14, min_periods=1).max().values
        denom  = high14 - low14
        k      = np.where(denom > 0, (c - low14) / denom * 100, 50.0)
        d      = rolling_mean(k, 3)
        g["STOCH_K"] = k
        g["STOCH_D"] = d

        # Bollinger Bands
        bb_m = sma20
        bb_s = rolling_std(c, 20)
        g["BB_upper"]  = bb_m + 2 * np.where(np.isnan(bb_s), 0, bb_s)
        g["BB_middle"] = bb_m
        g["BB_lower"]  = bb_m - 2 * np.where(np.isnan(bb_s), 0, bb_s)
        bb_range = g["BB_upper"].values - g["BB_lower"].values
        g["BB_pctB"]   = np.where(bb_range > 0, (c - g["BB_lower"].values) / bb_range, 0.5)
        g["bb_width"]  = np.where(bb_m > 0, bb_range / bb_m, 0)

        # ATR 14
        hl  = hi - lo
        hc  = np.abs(hi - np.roll(c, 1));  hc[0] = hl[0]
        lc  = np.abs(lo - np.roll(c, 1));  lc[0] = hl[0]
        tr  = np.maximum(hl, np.maximum(hc, lc))
        g["ATR_14"] = rolling_mean(tr, 14)

        # ADX / DI
        plus_dm  = np.where(np.diff(hi, prepend=hi[0]) > 0, np.diff(hi, prepend=hi[0]), 0.0)
        minus_dm = np.where(np.diff(lo, prepend=lo[0]) < 0, -np.diff(lo, prepend=lo[0]), 0.0)
        plus_dm  = np.where(plus_dm > minus_dm, plus_dm, 0.0)
        minus_dm = np.where(minus_dm > plus_dm, minus_dm, 0.0)
        tr14     = rolling_mean(tr, 14)
        di_plus  = np.where(tr14 > 0, rolling_mean(plus_dm,  14) / tr14 * 100, 0)
        di_minus = np.where(tr14 > 0, rolling_mean(minus_dm, 14) / tr14 * 100, 0)
        g["DI_plus"]  = di_plus
        g["DI_minus"] = di_minus
        di_sum  = di_plus + di_minus
        dx      = np.where(di_sum > 0, np.abs(di_plus - di_minus) / di_sum * 100, 0)
        g["ADX_14"] = rolling_mean(dx, 14)

        # OBV
        obv = np.cumsum(np.where(c_s.diff().fillna(0).values > 0, v,
                                 np.where(c_s.diff().fillna(0).values < 0, -v, 0)))
        g["OBV"] = obv

        # MFI 14
        typical = (hi + lo + c) / 3
        mf      = typical * v
        typ_diff = np.diff(typical, prepend=typical[0])
        pos_mf  = rolling_mean(np.where(typ_diff >= 0, mf, 0), 14)
        neg_mf  = rolling_mean(np.where(typ_diff <  0, mf, 0), 14)
        g["MFI_14"] = np.where(neg_mf > 0, 100 - 100 / (1 + pos_mf / neg_mf), 100)

        # Volume metrics
        vmean20  = rolling_mean(v, 20)
        g["Volume_Ratio_20"] = np.where(vmean20 > 0, v / vmean20, 1)
        v_s      = pd.Series(v)
        log_ret  = np.log(c_s / c_s.shift(1).replace(0, np.nan))
        g["HV_20"] = log_ret.rolling(20, min_periods=2).std().values * np.sqrt(252)

        # 52-week high/low
        hi_52  = pd.Series(hi).rolling(252, min_periods=1).max().values
        lo_52  = pd.Series(lo).rolling(252, min_periods=1).min().values
        g["High_52w_ratio"] = np.where(hi_52 > 0, c / hi_52, 1)
        g["Low_52w_ratio"]  = np.where(lo_52 > 0, c / lo_52, 1)

        # Candle
        body_range = hi - lo
        g["Candle_Body"]         = np.where(body_range > 0, np.abs(c - op) / body_range, 0)
        g["Candle_Upper_Shadow"] = np.where(body_range > 0, (hi - np.maximum(c, op)) / body_range, 0)
        g["Candle_Lower_Shadow"] = np.where(body_range > 0, (np.minimum(c, op) - lo) / body_range, 0)
        g["Candle_Direction"]    = np.sign(c - op)

        # Lag returns
        for lag in [1, 5, 20, 60, 120]:
            g[f"ret_lag_{lag}d"] = c_s.pct_change(lag).values

        # Volume ratios
        vmean5   = rolling_mean(v, 5)
        g["vol_ratio_5d"]  = np.where(vmean5  > 0, v / vmean5,  1)
        g["vol_ratio_20d"] = np.where(vmean20 > 0, v / vmean20, 1)
        g["vol_change_1d"] = v_s.pct_change(1).values
        g["vol_change_5d"] = v_s.pct_change(5).values

        # MA comparisons
        g["sma5_vs_sma20"]  = np.where(sma20 > 0, sma5  / sma20 - 1, 0)
        g["sma20_vs_sma60"] = np.where(sma60 > 0, sma20 / sma60 - 1, 0)
        g["close_vs_sma20"] = np.where(sma20 > 0, c / sma20 - 1, 0)
        g["close_vs_sma60"] = np.where(sma60 > 0, c / sma60 - 1, 0)

        # RSI / MACD deltas
        rsi_s  = pd.Series(g["RSI_14"].values)
        macd_s = pd.Series(macd)
        g["rsi_delta_5d"]  = rsi_s.diff(5).values
        g["macd_delta_5d"] = macd_s.diff(5).values

        # HV ratio
        hv_s   = pd.Series(g["HV_20"].values)
        hv_ma60 = hv_s.rolling(60, min_periods=1).mean().values
        g["hv_ratio"] = np.where(hv_ma60 > 0, g["HV_20"].values / hv_ma60, 1)

        # Rolling ret/vol stats
        ret1d = pd.Series(g["return_1d"].values)
        g["ret_roll_mean_20d"] = ret1d.rolling(20, min_periods=1).mean().values
        g["ret_roll_mean_60d"] = ret1d.rolling(60, min_periods=1).mean().values
        g["vol_roll_std_20d"]  = v_s.rolling(20, min_periods=1).std().values
        g["obv_roll_pct_20d"]  = pd.Series(obv).pct_change(20).values

        # RSI/MACD vs MA20
        rsi_ma20   = rsi_s.rolling(20, min_periods=1).mean().values
        macd_ma20  = macd_s.rolling(20, min_periods=1).mean().values
        g["rsi_vs_rsi_ma20"]   = g["RSI_14"].values - rsi_ma20
        g["macd_vs_macd_ma20"] = macd - macd_ma20

        # Stoch signals
        g["stoch_signal"]     = np.sign(k - d)
        stoch_ma20            = rolling_mean(k, 20)
        g["stoch_vs_ma20"]    = k - stoch_ma20
        g["stoch_overbought"] = (k > 80).astype(int)
        g["stoch_oversold"]   = (k < 20).astype(int)

        # MFI signals
        mfi    = g["MFI_14"].values
        mfi_ma20 = rolling_mean(mfi, 20)
        g["mfi_vs_ma20"]    = mfi - mfi_ma20
        g["mfi_overbought"] = (mfi > 80).astype(int)
        g["mfi_oversold"]   = (mfi < 20).astype(int)

        # BB width vs MA20
        bw     = g["bb_width"].values
        bw_ma20 = rolling_mean(bw, 20)
        g["bb_width_vs_ma20"] = np.where(bw_ma20 > 0, bw / bw_ma20 - 1, 0)

        # DI spread & ADX trend
        g["di_spread"]  = di_plus - di_minus
        g["adx_trend"]  = (g["ADX_14"].values > 25).astype(int)
        g["disparity_spread"] = g["Disparity_20"].values - g["Disparity_60"].values

        # Price position 20/60
        lo20 = pd.Series(c).rolling(20, min_periods=1).min().values
        hi20 = pd.Series(c).rolling(20, min_periods=1).max().values
        lo60 = pd.Series(c).rolling(60, min_periods=1).min().values
        hi60 = pd.Series(c).rolling(60, min_periods=1).max().values
        g["price_pos_20d"] = np.where(hi20 - lo20 > 0, (c - lo20) / (hi20 - lo20), 0.5)
        g["price_pos_60d"] = np.where(hi60 - lo60 > 0, (c - lo60) / (hi60 - lo60), 0.5)

        return g

    return df.groupby("ticker", group_keys=False).apply(calc).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  수급 피처 - 과거 rolling mean 으로 forward-fill
# ═══════════════════════════════════════════════════════════════════════════════
def add_supply_features_from_history(df: pd.DataFrame, master_parquet: str) -> pd.DataFrame:
    """
    master_test.parquet의 수급 피처를 신규 데이터에 연결.

    채움 전략 (LOCF -- Last Observation Carried Forward):
    1. 실제 수급 컬럼이 있으면 사용
    2. 없으면 종목별 마지막 관측값(LOCF)으로 채움
    3. 그래도 없으면 종목별 90일 평균으로 채움
    4. 끝까지 없으면 전체 중앙값으로 채움 (0-fill 금지)
    """
    supply_cols = ["Foreign_Net_Ratio", "Inst_Net_Ratio",
                   "Foreign_Net_MA5",   "Inst_Net_MA5",
                   "Short_Ratio_MA5",   "Short_Ratio_MA20"]

    try:
        hist = pd.read_parquet(master_parquet,
                               columns=["date", "종목코드"] + supply_cols,
                               engine="pyarrow")
        hist = hist.rename(columns={"종목코드": "ticker"})
        hist["date"] = pd.to_datetime(hist["date"])
        hist = hist.sort_values(["ticker", "date"])

        # ── LOCF: 종목별 마지막 관측값 ───────────────────────────────────────
        last_obs = (
            hist.groupby("ticker")[supply_cols]
            .last()
            .rename(columns={c: f"{c}_locf" for c in supply_cols})
        )

        # ── fallback: 최근 90일 평균 ─────────────────────────────────────────
        mean_90 = (
            hist.groupby("ticker")
            .tail(90)
            .groupby("ticker")[supply_cols]
            .mean()
            .rename(columns={c: f"{c}_mean90" for c in supply_cols})
        )

        # 전체 중앙값 (최후 fallback)
        global_med = {c: float(hist[c].median()) for c in supply_cols if c in hist.columns}

    except Exception as e:
        print(f"  [supply] 히스토리 로드 실패: {e}  → 전체 중앙값 0.0 사용")
        last_obs = pd.DataFrame()
        mean_90  = pd.DataFrame()
        global_med = {}

    for c in supply_cols:
        if c not in df.columns:
            df[c] = np.nan

    if not last_obs.empty:
        df = df.merge(last_obs,  on="ticker", how="left")
        df = df.merge(mean_90,   on="ticker", how="left")
        for c in supply_cols:
            locf_col  = f"{c}_locf"
            mean_col  = f"{c}_mean90"
            glob_val  = global_med.get(c, 0.0)
            # 우선순위: 실제값 > LOCF > 90일 평균 > 전체 중앙값
            df[c] = (
                df[c]
                .fillna(df.get(locf_col, np.nan))
                .fillna(df.get(mean_col, np.nan))
                .fillna(glob_val)
            )
            df.drop(columns=[locf_col, mean_col], inplace=True, errors="ignore")
        print(f"  [supply] LOCF 수급 피처 적용 완료 ({len(supply_cols)}개)")
    else:
        # 히스토리가 아예 없으면 전체 중앙값(또는 0)으로만 채움
        for c in supply_cols:
            df[c] = df[c].fillna(global_med.get(c, 0.0))
        print(f"  [supply] 히스토리 없음 -- 중앙값으로 채움")

    return df


# ═══════════════════════════════════════════════════════════════════════════════
#  fundamental 병합
# ═══════════════════════════════════════════════════════════════════════════════
def load_fundamentals() -> pd.DataFrame:
    per_path = PREP_DIR / "per_quarterly.csv"
    if not per_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(per_path, dtype={"종목코드": str})
    qe_map = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
    df["quarter_date"] = pd.to_datetime(
        df["연도"].astype(str) + "-" + df["분기"].map(qe_map), errors="coerce")
    df = df.rename(columns={"종목코드": "ticker"})
    return df[["ticker", "quarter_date", "PER", "PBR", "EPS", "BPS", "DPS"]].sort_values(
        ["ticker", "quarter_date"])


def merge_fundamentals(df_feat: pd.DataFrame, df_fund: pd.DataFrame) -> pd.DataFrame:
    if df_fund.empty:
        for c in ["PER", "PBR", "EPS", "BPS", "DPS"]:
            if c not in df_feat.columns:
                df_feat[c] = np.nan
        return df_feat

    results = []
    for ticker, gfeat in df_feat.groupby("ticker"):
        gfund = df_fund[df_fund["ticker"] == ticker].sort_values("quarter_date")
        if gfund.empty:
            for c in ["PER", "PBR", "EPS", "BPS", "DPS"]:
                gfeat[c] = np.nan
            results.append(gfeat)
            continue
        gfeat = gfeat.sort_values("date")
        merged = pd.merge_asof(
            gfeat.reset_index(drop=True),
            gfund[["quarter_date", "PER", "PBR", "EPS", "BPS", "DPS"]].rename(
                columns={"quarter_date": "date"}),
            on="date", direction="backward"
        )
        results.append(merged)

    return pd.concat(results, ignore_index=True) if results else df_feat


# ═══════════════════════════════════════════════════════════════════════════════
#  market context (지수/FX)
# ═══════════════════════════════════════════════════════════════════════════════
def merge_market_context(df: pd.DataFrame) -> pd.DataFrame:
    idx_path = PIPE_DIR / "raw_index_fx.parquet"
    if not idx_path.exists():
        # 기존 kospi.csv, fx_usdkrw.csv 활용
        k_path = BASE_DIR / "importantdata/kospi.csv"
        fx_path = BASE_DIR / "importantdata/fx_usdkrw.csv"
        dfs = []
        if k_path.exists():
            dk = pd.read_csv(k_path, encoding="utf-8-sig")
            dk.columns = ["date" if "일" in c or i == 0 else c
                          for i, c in enumerate(dk.columns)]
            dk["date"] = pd.to_datetime(dk.iloc[:, 0], errors="coerce").dt.date.astype(str)
            if len(dk.columns) >= 6:
                dk = dk.rename(columns={dk.columns[5]: "kospi_close"})
                dfs.append(dk[["date", "kospi_close"]])
        if fx_path.exists():
            dfx = pd.read_csv(fx_path, encoding="utf-8-sig")
            dfx.columns = ["date", "fx_usdkrw"]
            dfx["date"] = pd.to_datetime(dfx["date"], errors="coerce").dt.date.astype(str)
            dfs.append(dfx)
        if dfs:
            from functools import reduce
            ctx = reduce(lambda a, b: pd.merge(a, b, on="date", how="outer"), dfs)
        else:
            return df
    else:
        ctx = pd.read_parquet(idx_path)
        ctx["date"] = pd.to_datetime(ctx["date"]).dt.date.astype(str)

    ctx = ctx.sort_values("date")
    df["date_str"] = df["date"].astype(str).str[:10]
    df = df.merge(ctx, left_on="date_str", right_on="date", how="left",
                  suffixes=("", "_ctx"))
    df.drop(columns=["date_str"] + [c for c in df.columns if c.endswith("_ctx")],
            inplace=True, errors="ignore")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
#  DuckDB prices 테이블 업데이트 (market_data.duckdb 스키마 대응)
# ═══════════════════════════════════════════════════════════════════════════════
def update_duckdb_prices(df_ohlcv: pd.DataFrame, df_tech: pd.DataFrame):
    """
    market_data.duckdb prices 테이블 스키마:
      ticker, date(BIGINT YYYYMMDD), market_cap, shares_outstanding,
      open, high, low, close, volume, amount,
      upper_limit, lower_limit, foreign_shares, foreign_ratio,
      foreign_limit_shares, individual_amount, foreign_amount,
      other_corp_amount, pension_amount, trust_amount, insurance_amount,
      bank_amount, other_fin_amount, short_volume, total_volume,
      short_ratio, inst_total_amount
    KRX MDCSTAT01501 에서 수집한 컬럼만 INSERT 하고 나머지는 NULL.
    """
    print("\nUpdating DuckDB prices table...")

    # date를 BIGINT(YYYYMMDD) 로 변환
    df_p = df_ohlcv[["ticker", "date", "open", "high", "low",
                      "close", "volume", "amount", "market_cap"]].copy()
    df_p["date"] = pd.to_datetime(df_p["date"]).dt.strftime("%Y%m%d").astype(int)

    # 수치 정수 변환 (DuckDB BIGINT)
    for c in ["open", "high", "low", "close", "volume", "amount", "market_cap"]:
        df_p[c] = pd.to_numeric(df_p[c], errors="coerce").fillna(0).astype(np.int64)

    con = duckdb.connect(str(DUCKDB))

    # 이미 존재하는 (ticker, date) 쌍 제거 → 중복 삽입 방지
    try:
        existing = con.execute(
            "SELECT ticker, date FROM prices WHERE date >= ?",
            [int(df_p["date"].min())]
        ).fetchdf()
        if not existing.empty:
            existing_set = set(zip(existing["ticker"], existing["date"].astype(int)))
            mask = [
                (row.ticker, row.date) not in existing_set
                for row in df_p.itertuples(index=False)
            ]
            df_p = df_p[mask].reset_index(drop=True)
    except Exception as e:
        print(f"  [warn] 중복 체크 실패: {e}")

    if df_p.empty:
        print("  No new rows to insert (all dates already exist).")
        con.close()
        return

    # 배치 INSERT (INSERT INTO ... SELECT * FROM df)
    con.register("_new_prices", df_p)
    con.execute("""
        INSERT INTO prices
          (ticker, date, open, high, low, close, volume, amount, market_cap)
        SELECT ticker, date, open, high, low, close, volume, amount, market_cap
        FROM _new_prices
    """)
    con.unregister("_new_prices")
    con.close()
    print(f"  Inserted {len(df_p):,} rows into prices")


# ═══════════════════════════════════════════════════════════════════════════════
#  메인
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start",      default=None)
    parser.add_argument("--end",        default=None)
    parser.add_argument("--no-collect", action="store_true",
                        help="Skip collection, rebuild features only")
    # 보안 — KRX 로그인 자격은 환경변수 또는 명시 CLI 필수. plaintext default 제거.
    # 사용: export KRX_ID=... KRX_PW=... 또는 --id ... --pw ...
    parser.add_argument("--id", default=os.getenv("KRX_ID"))
    parser.add_argument("--pw", default=os.getenv("KRX_PW"))
    args = parser.parse_args()
    if not args.no_collect and (not args.id or not args.pw):
        parser.error("KRX 자격 필요. env KRX_ID·KRX_PW 또는 --id·--pw 명시.")

    # 날짜 결정
    if args.start is None:
        try:
            con = duckdb.connect(str(DUCKDB), read_only=True)
            max_date = con.execute("SELECT MAX(date) FROM prices").fetchone()[0]
            con.close()
            if max_date is None:
                raise ValueError("prices 테이블이 비어 있습니다.")
            # prices.date 는 BIGINT (YYYYMMDD) 형식
            max_date_str = str(int(max_date))  # e.g. "20251230"
            start_dt = (pd.to_datetime(max_date_str, format="%Y%m%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"[ERROR] DuckDB 날짜 조회 실패: {e}")
            print("  --start 옵션으로 시작일을 직접 지정하세요. (예: --start 2026-01-01)")
            sys.exit(1)
    else:
        start_dt = args.start

    end_dt  = args.end or date.today().strftime("%Y-%m-%d")
    start_krx = start_dt.replace("-", "")
    end_krx   = end_dt.replace("-", "")

    # seed
    df_seed = pd.read_csv(SEED_FILE, dtype={"ticker": str})
    df_seed["ticker"] = df_seed["ticker"].str.zfill(6)
    seed_tickers = set(df_seed["ticker"].tolist())
    print(f"Seed tickers: {len(seed_tickers)}")
    print(f"Collection range: {start_dt} ~ {end_dt}")

    # ── 수집 ──────────────────────────────────────────────────────────────────
    if not args.no_collect:
        print("\nLogging into KRX...")
        if not login_krx(args.id, args.pw):
            sys.exit(1)
        df_ohlcv = collect_all(start_krx, end_krx, seed_tickers)
        if df_ohlcv.empty:
            print("\nNo new OHLCV data. Exiting.")
            return
    else:
        raw_path = PIPE_DIR / "raw_ohlcv.parquet"
        if not raw_path.exists():
            print("raw_ohlcv.parquet not found. Run without --no-collect first.")
            sys.exit(1)
        df_ohlcv = pd.read_parquet(raw_path)
        df_ohlcv["date"] = pd.to_datetime(df_ohlcv["date"])
        print(f"Loaded raw_ohlcv: {len(df_ohlcv):,} rows")

    # ── 피처 엔지니어링 ────────────────────────────────────────────────────────
    print("\nBuilding features...")

    # 기존 prices 로드 (warm-up용)
    print("  Loading existing price history from DuckDB...")
    con = duckdb.connect(str(DUCKDB), read_only=True)
    tickers_str = ",".join(f"'{t}'" for t in seed_tickers)
    df_hist = con.execute(f"""
        SELECT ticker, date, open, high, low, close, volume, amount, market_cap
        FROM prices WHERE ticker IN ({tickers_str})
        ORDER BY ticker, date
    """).fetchdf()
    con.close()
    # prices.date 는 BIGINT (YYYYMMDD) → datetime 변환
    df_hist["date"] = pd.to_datetime(df_hist["date"].astype(str), format="%Y%m%d")
    print(f"  Historical: {len(df_hist):,} rows")

    # 합산
    df_combined = pd.concat([
        df_hist[["ticker","date","open","high","low","close","volume","amount","market_cap"]],
        df_ohlcv[["ticker","date","open","high","low","close","volume","amount","market_cap"]]
    ], ignore_index=True).drop_duplicates(["ticker","date"]).sort_values(["ticker","date"])
    print(f"  Combined: {len(df_combined):,} rows  ->  computing technical indicators...")

    df_tech = compute_technical(df_combined)

    # 신규 날짜만 필터
    new_dates = set(df_ohlcv["date"].astype(str).str[:10].unique())
    df_new = df_tech[df_tech["date"].astype(str).str[:10].isin(new_dates)].copy()
    print(f"  New feature rows: {len(df_new):,}")

    # 수급 피처 (히스토리 평균 forward-fill)
    master_path = str(BASE_DIR / "models/v7_alpha_target/dataset/master_test.parquet")
    df_new = add_supply_features_from_history(df_new, master_path)

    # fundamental 병합
    print("  Merging fundamentals...")
    df_fund = load_fundamentals()
    df_new  = merge_fundamentals(df_new, df_fund)

    # 시장 지수/FX 병합
    print("  Merging market context (index/FX)...")
    df_new = merge_market_context(df_new)

    # 저장
    out_path = PIPE_DIR / "new_features.parquet"
    df_new.to_parquet(out_path, index=False)
    print(f"\nSaved new_features.parquet: {len(df_new):,} rows x {len(df_new.columns)} cols")
    print(f"  Date range: {df_new['date'].min()} ~ {df_new['date'].max()}")

    # DuckDB prices 업데이트
    update_duckdb_prices(df_ohlcv, df_tech)

    print("\nDone! Next step: run daily_inference.py")


if __name__ == "__main__":
    main()

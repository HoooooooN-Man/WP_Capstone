from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional

import pandas as pd
import requests

PYKRX_IMPORT_ERROR: Exception | None = None
try:
    from pykrx import stock
except Exception as exc:  # pragma: no cover
    stock = None
    PYKRX_IMPORT_ERROR = exc


# =============================================================================
# KRX endpoints / constants
# =============================================================================

KOSPI200_INDEX_CODE = "1028"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

LOGIN_PAGE = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001.cmd"
LOGIN_JSP = "https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp?site=mdc"
LOGIN_URL = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001D1.cmd"
DATA_URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
OTP_URL = "https://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
DOWNLOAD_CSV_URL = "https://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd",
    "X-Requested-With": "XMLHttpRequest",
}
DOWNLOAD_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd",
}

MARKET_TO_KRX = {
    "KOSPI": "STK",
    "KOSDAQ": "KSQ",
    "KONEX": "KNX",
    "ALL": "ALL",
}

# KRX bld values used in this script.
BLD_MARKET_OHLCV = "dbms/MDC/STAT/standard/MDCSTAT01501"
BLED_MARKET_FUNDAMENTAL = "dbms/MDC/STAT/standard/MDCSTAT03501"
BLD_INDEX_CONSTITUENTS = "dbms/MDC/STAT/standard/MDCSTAT00601"


# =============================================================================
# Utility helpers
# =============================================================================


def parse_date_yyyymmdd(value: str) -> str:
    value = str(value).strip()
    if re.fullmatch(r"\d{8}", value):
        return value
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    raise ValueError(f"지원하지 않는 날짜 형식입니다: {value}")



def yyyymmdd_to_iso(value: str) -> str:
    return datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")



def now_local_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")



def to_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return float(value)
    text = str(value).strip()
    if text in {"", "-", "N/A", "nan", "None"}:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None



def to_int(value: Any) -> Optional[int]:
    num = to_number(value)
    if num is None:
        return None
    return int(round(num))



def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)



def delete_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()



def first_present(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return None



def recursive_find_records(payload: Any) -> list[dict[str, Any]]:
    """Return the first list of dict records found in a nested payload."""
    if isinstance(payload, list):
        if payload and all(isinstance(x, dict) for x in payload):
            return payload
        for item in payload:
            found = recursive_find_records(item)
            if found:
                return found
        return []

    if isinstance(payload, dict):
        for preferred in (
            "output",
            "OutBlock_1",
            "OutBlock",
            "result",
            "block1",
            "DATA",
            "data",
        ):
            if preferred in payload:
                found = recursive_find_records(payload[preferred])
                if found:
                    return found
        for value in payload.values():
            found = recursive_find_records(value)
            if found:
                return found
    return []



def normalize_table(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame.from_records(records)


# =============================================================================
# KRX client
# =============================================================================


class KrxAuthError(RuntimeError):
    pass


class KrxDataError(RuntimeError):
    pass


@dataclass
class SnapshotPaths:
    root: Path
    daily_dir: Path
    monthly_dir: Path
    current_dir: Path


class KrxClient:
    def __init__(self, login_id: str, login_pw: str, timeout: int = 20, verbose: bool = True) -> None:
        self.login_id = login_id
        self.login_pw = login_pw
        self.timeout = timeout
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def log(self, message: str) -> None:
        if self.verbose:
            print(message, flush=True)

    def login(self) -> None:
        self.log("[1/6] KRX 로그인 시도")
        self.session.get(LOGIN_PAGE, headers={"User-Agent": USER_AGENT}, timeout=self.timeout)
        self.session.get(
            LOGIN_JSP,
            headers={"User-Agent": USER_AGENT, "Referer": LOGIN_PAGE},
            timeout=self.timeout,
        )

        payload = {
            "mbrNm": "",
            "telNo": "",
            "di": "",
            "certType": "",
            "mbrId": self.login_id,
            "pw": self.login_pw,
        }
        resp = self.session.post(
            LOGIN_URL,
            data=payload,
            headers={**REQUEST_HEADERS, "Referer": LOGIN_PAGE},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        error_code = data.get("_error_code", "")

        if error_code == "CD011":
            payload["skipDup"] = "Y"
            resp = self.session.post(
                LOGIN_URL,
                data=payload,
                headers={**REQUEST_HEADERS, "Referer": LOGIN_PAGE},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            error_code = data.get("_error_code", "")

        if error_code != "CD001":
            raise KrxAuthError(f"KRX 로그인 실패: error_code={error_code}, body={data}")

        self.log("  └─ 로그인 성공")

    def _post_json(self, data: dict[str, Any], *, allow_relogin: bool = True) -> Any:
        resp = self.session.post(DATA_URL, headers=REQUEST_HEADERS, data=data, timeout=self.timeout)
        text = resp.text.strip()

        if resp.status_code != 200 or text in {"LOGOUT", ""}:
            if allow_relogin:
                self.log("  └─ 세션 만료 감지, 재로그인 후 재시도")
                self.login()
                return self._post_json(data, allow_relogin=False)
            raise KrxDataError(
                f"KRX JSON 요청 실패: status={resp.status_code}, body={text[:300]}"
            )

        try:
            return resp.json()
        except ValueError as exc:
            if allow_relogin and "LOGOUT" in text.upper():
                self.login()
                return self._post_json(data, allow_relogin=False)
            raise KrxDataError(f"JSON 파싱 실패: {text[:300]}") from exc

    def _post_csv(self, form: dict[str, Any], *, allow_relogin: bool = True) -> pd.DataFrame:
        otp_resp = self.session.post(OTP_URL, headers=DOWNLOAD_HEADERS, data=form, timeout=self.timeout)
        otp_resp.raise_for_status()
        otp = otp_resp.text.strip()
        if otp in {"", "LOGOUT"}:
            if allow_relogin:
                self.log("  └─ OTP 발급 중 세션 만료, 재로그인 후 재시도")
                self.login()
                return self._post_csv(form, allow_relogin=False)
            raise KrxDataError(f"OTP 발급 실패: {otp!r}")

        file_resp = self.session.post(
            DOWNLOAD_CSV_URL,
            headers=DOWNLOAD_HEADERS,
            data={"code": otp},
            timeout=self.timeout,
        )
        file_resp.raise_for_status()
        raw = file_resp.content

        for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
            try:
                return pd.read_csv(io.BytesIO(raw), encoding=encoding)
            except Exception:
                continue

        raise KrxDataError("CSV 다운로드 파싱 실패")

    def fetch_market_ohlcv(self, date_yyyymmdd: str, market: str = "ALL") -> pd.DataFrame:
        market_id = MARKET_TO_KRX[market.upper()]
        payload = {
            "bld": BLD_MARKET_OHLCV,
            "locale": "ko_KR",
            "mktId": market_id,
            "trdDd": date_yyyymmdd,
            "share": "1",
            "money": "1",
            "csvxls_isNo": "false",
        }

        try:
            data = self._post_json(payload)
            records = recursive_find_records(data)
            df = normalize_table(records)
            if not df.empty:
                return df
        except Exception as exc:
            self.log(f"  └─ OHLCV JSON 조회 실패, CSV fallback 사용: {exc}")

        csv_form = {
            "mktId": market_id,
            "trdDd": date_yyyymmdd,
            "share": "1",
            "money": "1",
            "csvxls_isNo": "false",
            "name": "fileDown",
            "url": BLD_MARKET_OHLCV,
        }
        return self._post_csv(csv_form)

    def fetch_market_fundamental(self, date_yyyymmdd: str, market: str = "ALL") -> pd.DataFrame:
        market_id = MARKET_TO_KRX[market.upper()]
        payload = {
            "bld": BLED_MARKET_FUNDAMENTAL,
            "locale": "ko_KR",
            "mktId": market_id,
            "trdDd": date_yyyymmdd,
            "csvxls_isNo": "false",
        }

        try:
            data = self._post_json(payload)
            records = recursive_find_records(data)
            df = normalize_table(records)
            if not df.empty:
                return df
        except Exception as exc:
            self.log(f"  └─ Fundamental JSON 조회 실패, CSV fallback 사용: {exc}")

        csv_form = {
            "searchType": "1",
            "mktId": market_id,
            "trdDd": date_yyyymmdd,
            "csvxls_isNo": "false",
            "name": "fileDown",
            "url": BLED_MARKET_FUNDAMENTAL,
        }
        return self._post_csv(csv_form)

    @contextlib.contextmanager
    def patched_requests_for_pykrx(self) -> Iterator[None]:
        """
        Force requests.get/post/request used by pykrx to go through the
        authenticated KRX session.
        """
        import requests as _requests

        original_request = _requests.request
        original_get = _requests.get
        original_post = _requests.post

        def patched_request(method: str, url: str, **kwargs: Any):
            return self.session.request(method=method, url=url, **kwargs)

        def patched_get(url: str, **kwargs: Any):
            return self.session.get(url, **kwargs)

        def patched_post(url: str, **kwargs: Any):
            return self.session.post(url, **kwargs)

        _requests.request = patched_request
        _requests.get = patched_get
        _requests.post = patched_post
        try:
            yield
        finally:
            _requests.request = original_request
            _requests.get = original_get
            _requests.post = original_post

    def fetch_index_constituents(self, date_yyyymmdd: str, index_ticker: str) -> pd.DataFrame:
        """
        KRX 지수구성종목(11006) 조회.
        pykrx 내부 구현을 따라 indTpCd=ticker[0], indTpCd2=ticker[1:] 형식으로 호출한다.
        예) 코스피200 1028 -> indTpCd=1, indTpCd2=028
        """
        index_ticker = str(index_ticker).strip()
        if not index_ticker or len(index_ticker) < 2:
            raise ValueError(f"잘못된 지수 코드입니다: {index_ticker!r}")

        ind_tp_cd = index_ticker[0]
        ind_tp_cd2 = index_ticker[1:]
        payload = {
            "bld": BLD_INDEX_CONSTITUENTS,
            "locale": "ko_KR",
            "trdDd": date_yyyymmdd,
            "indTpCd": ind_tp_cd,
            "indTpCd2": ind_tp_cd2,
            "csvxls_isNo": "false",
        }

        try:
            data = self._post_json(payload)
            records = recursive_find_records(data)
            df = normalize_table(records)
            if not df.empty:
                return df
        except Exception as exc:
            self.log(f"  └─ 지수구성종목 JSON 조회 실패, CSV fallback 사용: {exc}")

        csv_form = {
            "trdDd": date_yyyymmdd,
            "indTpCd": ind_tp_cd,
            "indTpCd2": ind_tp_cd2,
            "csvxls_isNo": "false",
            "name": "fileDown",
            "url": BLD_INDEX_CONSTITUENTS,
        }
        return self._post_csv(csv_form)

    def get_kospi200_tickers(self, date_yyyymmdd: str) -> list[str]:
        direct_exc: Exception | None = None
        try:
            df = self.fetch_index_constituents(date_yyyymmdd, KOSPI200_INDEX_CODE)
            if not df.empty:
                ticker_col = None
                for col in ("ISU_SRT_CD", "종목코드", "티커", "short_code"):
                    if col in df.columns:
                        ticker_col = col
                        break
                if ticker_col is None and df.index.name in {"ISU_SRT_CD", "종목코드", "티커"}:
                    values = df.index.tolist()
                elif ticker_col is not None:
                    values = df[ticker_col].tolist()
                else:
                    values = []

                tickers = sorted({str(t).zfill(6) for t in values if str(t).strip()})
                if tickers:
                    self.log("  └─ KRX requests로 구성종목 조회 성공")
                    return tickers
        except Exception as exc:
            direct_exc = exc
            self.log(f"  └─ KRX requests 지수구성종목 조회 실패: {exc}")

        last_exc: Exception | None = None
        if stock is not None:
            with self.patched_requests_for_pykrx():
                for _ in range(2):
                    try:
                        pdf = stock.get_index_portfolio_deposit_file(KOSPI200_INDEX_CODE, date_yyyymmdd)
                        tickers = sorted({str(t).zfill(6) for t in pdf})
                        if tickers:
                            self.log("  └─ pykrx fallback으로 구성종목 조회 성공")
                            return tickers
                    except Exception as exc:  # pragma: no cover
                        last_exc = exc
                        self.log(f"  └─ pykrx KOSPI200 구성종목 조회 재시도: {exc}")
                        self.login()
                        time.sleep(0.5)
        else:
            last_exc = PYKRX_IMPORT_ERROR

        extra_hint = ""
        if last_exc is not None and "pkg_resources" in str(last_exc):
            extra_hint = " (pykrx fallback 사용 시 `python -m pip install setuptools` 필요 가능)"
        raise RuntimeError(
            "KOSPI200 구성종목을 가져오지 못했습니다. "
            f"KRX direct 오류={direct_exc}; pykrx 오류={last_exc}{extra_hint}"
        )


# =============================================================================
# Data shaping
# =============================================================================


def standardize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ticker", "name", "open", "high", "low", "close", "volume", "amount", "change_pct"])

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rec = row.to_dict()
        ticker = first_present(rec, "티커", "종목코드", "ISU_SRT_CD")
        name = first_present(rec, "종목명", "한글 종목약명", "ISU_ABBRV", "ISU_ABBRV_NM")
        if ticker is None:
            continue
        rows.append(
            {
                "ticker": str(ticker).zfill(6),
                "name": first_present(rec, "종목명", "한글 종목약명", "ISU_ABBRV", "ISU_ABBRV_NM"),
                "market": first_present(rec, "시장구분", "MKT_NM", "MKT_ID"),
                "sector": first_present(rec, "소속부", "SECT_TP_NM", "업종명"),
                "open": to_int(first_present(rec, "시가", "TDD_OPNPRC", "OPNPRC")),
                "high": to_int(first_present(rec, "고가", "TDD_HGPRC", "HGPRC")),
                "low": to_int(first_present(rec, "저가", "TDD_LWPRC", "LWPRC")),
                "close": to_int(first_present(rec, "종가", "TDD_CLSPRC", "CLSPRC")),
                "volume": to_int(first_present(rec, "거래량", "ACC_TRDVOL", "TRDVOL")),
                "amount": to_int(first_present(rec, "거래대금", "ACC_TRDVAL", "TRDVAL")),
                "change_pct": to_number(first_present(rec, "등락률", "FLUC_RT")),
            }
        )
    return pd.DataFrame(rows).drop_duplicates(subset=["ticker"], keep="last")



def standardize_fundamental(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ticker", "bps", "per", "pbr", "eps", "div", "dps", "fwd_per"])

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rec = row.to_dict()
        ticker = first_present(rec, "티커", "종목코드", "ISU_SRT_CD")
        if ticker is None:
            continue
        rows.append(
            {
                "ticker": str(ticker).zfill(6),
                "bps": to_int(first_present(rec, "BPS")),
                "per": to_number(first_present(rec, "PER")),
                "pbr": to_number(first_present(rec, "PBR")),
                "eps": to_int(first_present(rec, "EPS")),
                "div": to_number(first_present(rec, "DIV", "배당수익률")),
                "dps": to_int(first_present(rec, "DPS")),
                "fwd_per": to_number(first_present(rec, "FWD_PER", "선행PER")),
            }
        )
    return pd.DataFrame(rows).drop_duplicates(subset=["ticker"], keep="last")



def build_snapshot_dataframe(
    as_of: str,
    kospi200_tickers: Iterable[str],
    ohlcv_raw: pd.DataFrame,
    fundamental_raw: pd.DataFrame,
) -> pd.DataFrame:
    kospi200_set = {str(t).zfill(6) for t in kospi200_tickers}
    ohlcv = standardize_ohlcv(ohlcv_raw)
    fundamental = standardize_fundamental(fundamental_raw)

    if ohlcv.empty:
        raise KrxDataError("OHLCV 정규화 결과가 비어 있습니다.")

    merged = ohlcv.merge(fundamental, on="ticker", how="left")
    merged = merged[merged["ticker"].isin(kospi200_set)].copy()

    if merged.empty:
        raise KrxDataError("KOSPI200 필터링 결과가 비어 있습니다.")

    merged.insert(0, "snapshot_date", yyyymmdd_to_iso(as_of))
    merged.insert(1, "index_code", KOSPI200_INDEX_CODE)
    merged.insert(2, "index_name", "KOSPI 200")
    merged["member_yn"] = True
    merged["collected_at"] = now_local_str()
    merged["source"] = "krx_data_marketplace"

    preferred_columns = [
        "snapshot_date",
        "index_code",
        "index_name",
        "ticker",
        "name",
        "market",
        "sector",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "change_pct",
        "bps",
        "per",
        "pbr",
        "eps",
        "div",
        "dps",
        "fwd_per",
        "member_yn",
        "collected_at",
        "source",
    ]
    for col in preferred_columns:
        if col not in merged.columns:
            merged[col] = None

    merged = merged[preferred_columns].sort_values(["ticker"]).reset_index(drop=True)
    return merged


# =============================================================================
# Snapshot storage and retention
# =============================================================================


def build_paths(base_dir: Path) -> SnapshotPaths:
    root = base_dir / "market_snapshots" / "kospi200"
    daily_dir = root / "daily"
    monthly_dir = root / "monthly"
    current_dir = root / "current"
    for path in (daily_dir, monthly_dir, current_dir):
        path.mkdir(parents=True, exist_ok=True)
    return SnapshotPaths(root=root, daily_dir=daily_dir, monthly_dir=monthly_dir, current_dir=current_dir)



def save_snapshot_files(df: pd.DataFrame, as_of: str, paths: SnapshotPaths) -> dict[str, Path]:
    # Daily snapshot
    daily_path = paths.daily_dir / as_of
    daily_path.mkdir(parents=True, exist_ok=True)
    daily_csv = daily_path / f"kospi200_{as_of}.csv"
    daily_json = daily_path / f"kospi200_{as_of}.json"
    df.to_csv(daily_csv, index=False, encoding="utf-8-sig")
    df.to_json(daily_json, orient="records", force_ascii=False, indent=2)

    # Current latest snapshot
    latest_csv = paths.current_dir / "kospi200_latest.csv"
    latest_json = paths.current_dir / "kospi200_latest.json"
    df.to_csv(latest_csv, index=False, encoding="utf-8-sig")
    df.to_json(latest_json, orient="records", force_ascii=False, indent=2)

    # Monthly snapshot: overwrite same YYYYMM during the month, older months remain frozen.
    ym = as_of[:6]
    year = as_of[:4]
    monthly_path = paths.monthly_dir / year
    monthly_path.mkdir(parents=True, exist_ok=True)
    monthly_csv = monthly_path / f"kospi200_{ym}.csv"
    monthly_json = monthly_path / f"kospi200_{ym}.json"
    df.to_csv(monthly_csv, index=False, encoding="utf-8-sig")
    df.to_json(monthly_json, orient="records", force_ascii=False, indent=2)

    manifest = {
        "dataset": "kospi200_daily_snapshot",
        "index_code": KOSPI200_INDEX_CODE,
        "index_name": "KOSPI 200",
        "as_of": as_of,
        "as_of_iso": yyyymmdd_to_iso(as_of),
        "row_count": int(len(df)),
        "latest_csv": latest_csv.as_posix(),
        "latest_json": latest_json.as_posix(),
        "daily_csv": daily_csv.as_posix(),
        "daily_json": daily_json.as_posix(),
        "monthly_csv": monthly_csv.as_posix(),
        "monthly_json": monthly_json.as_posix(),
        "updated_at": now_local_str(),
    }
    manifest_path = paths.current_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        "daily_csv": daily_csv,
        "daily_json": daily_json,
        "latest_csv": latest_csv,
        "latest_json": latest_json,
        "monthly_csv": monthly_csv,
        "monthly_json": monthly_json,
        "manifest": manifest_path,
    }



def prune_daily_snapshots(paths: SnapshotPaths, keep_days: int) -> list[Path]:
    snapshot_dirs = []
    for child in paths.daily_dir.iterdir():
        if child.is_dir() and re.fullmatch(r"\d{8}", child.name):
            snapshot_dirs.append(child)

    snapshot_dirs.sort(key=lambda p: p.name, reverse=True)
    to_delete = snapshot_dirs[keep_days:]
    for old in to_delete:
        delete_path(old)
    return to_delete


def save_constituents_cache(paths: SnapshotPaths, tickers: Iterable[str], as_of: str) -> Path:
    cache_path = paths.current_dir / "kospi200_constituents_latest.json"
    payload = {
        "index_code": KOSPI200_INDEX_CODE,
        "index_name": "KOSPI 200",
        "as_of": as_of,
        "saved_at": now_local_str(),
        "ticker_count": len({str(t).zfill(6) for t in tickers}),
        "tickers": sorted({str(t).zfill(6) for t in tickers}),
    }
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return cache_path



def load_cached_constituents(paths: SnapshotPaths) -> list[str]:
    cache_json = paths.current_dir / "kospi200_constituents_latest.json"
    if cache_json.exists():
        try:
            payload = json.loads(cache_json.read_text(encoding="utf-8"))
            tickers = payload.get("tickers", [])
            tickers = sorted({str(t).zfill(6) for t in tickers if str(t).strip()})
            if tickers:
                return tickers
        except Exception:
            pass

    latest_csv = paths.current_dir / "kospi200_latest.csv"
    if latest_csv.exists():
        try:
            df = pd.read_csv(latest_csv, dtype={"ticker": str, "종목코드": str})
            ticker_col = "ticker" if "ticker" in df.columns else "종목코드" if "종목코드" in df.columns else None
            if ticker_col is not None:
                tickers = sorted({str(t).zfill(6) for t in df[ticker_col].dropna().astype(str).tolist() if str(t).strip()})
                if tickers:
                    return tickers
        except Exception:
            pass

    daily_dirs = sorted(
        [p for p in paths.daily_dir.iterdir() if p.is_dir() and re.fullmatch(r"\d{8}", p.name)],
        key=lambda p: p.name,
        reverse=True,
    )
    for day_dir in daily_dirs:
        csv_path = day_dir / f"kospi200_{day_dir.name}.csv"
        if not csv_path.exists():
            continue
        try:
            df = pd.read_csv(csv_path, dtype={"ticker": str, "종목코드": str})
            ticker_col = "ticker" if "ticker" in df.columns else "종목코드" if "종목코드" in df.columns else None
            if ticker_col is None:
                continue
            tickers = sorted({str(t).zfill(6) for t in df[ticker_col].dropna().astype(str).tolist() if str(t).strip()})
            if tickers:
                return tickers
        except Exception:
            continue

    return []


# =============================================================================
# Business date resolution
# =============================================================================


def find_latest_business_day(client: KrxClient, max_lookback: int = 14) -> str:
    today = datetime.now()
    for days in range(max_lookback + 1):
        dt = today - timedelta(days=days)
        if dt.weekday() >= 5:  # Saturday/Sunday
            continue
        candidate = dt.strftime("%Y%m%d")
        try:
            df = client.fetch_market_ohlcv(candidate, market="KOSPI")
            std = standardize_ohlcv(df)
            if not std.empty:
                return candidate
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("최근 영업일을 찾지 못했습니다.")


# =============================================================================
# Main execution
# =============================================================================


def load_env_fallback() -> tuple[dict[str, str], Path | None]:
    env: dict[str, str] = {}
    script_dir = Path(__file__).resolve().parent
    candidates: list[Path] = []

    for candidate in [
        Path.cwd() / ".env",
        script_dir / ".env",
        script_dir.parent / ".env",
        script_dir.parent.parent / ".env",
    ]:
        if candidate not in candidates:
            candidates.append(candidate)

    env_file = next((p for p in candidates if p.exists()), None)
    if env_file is None:
        return env, None

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env, env_file



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="KRX 로그인 세션을 이용해 KOSPI200 일별/월별 스냅샷을 저장합니다."
    )
    parser.add_argument("--login-id", default=None, help="KRX 로그인 아이디")
    parser.add_argument("--login-pw", default=None, help="KRX 로그인 비밀번호")
    parser.add_argument(
        "--as-of-date",
        default=None,
        help="기준일 (YYYYMMDD 또는 YYYY-MM-DD). 미지정 시 최근 영업일 자동 탐색",
    )
    parser.add_argument(
        "--base-dir",
        default="data",
        help="스냅샷 저장 루트 디렉터리 (기본: data)",
    )
    parser.add_argument(
        "--keep-daily",
        type=int,
        default=30,
        help="유지할 일별 스냅샷 개수 (기본: 30)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="로그를 최소화합니다.",
    )
    return parser.parse_args()



def resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    env_map, env_path = load_env_fallback()
    if env_path is not None and not args.quiet:
        print(f".env 로드: {env_path}")
    login_id = args.login_id or os.getenv("KRX_LOGIN_ID") or env_map.get("KRX_LOGIN_ID")
    login_pw = args.login_pw or os.getenv("KRX_LOGIN_PW") or env_map.get("KRX_LOGIN_PW")
    if not login_id or not login_pw:
        raise SystemExit(
            "KRX 로그인 정보가 없습니다. --login-id/--login-pw 또는 "
            "환경변수 KRX_LOGIN_ID/KRX_LOGIN_PW(.env 포함)를 설정하세요."
        )
    return login_id, login_pw



def main() -> int:
    args = parse_args()
    login_id, login_pw = resolve_credentials(args)
    client = KrxClient(login_id=login_id, login_pw=login_pw, verbose=not args.quiet)
    paths = build_paths(Path(args.base_dir))

    client.login()

    if args.as_of_date:
        as_of = parse_date_yyyymmdd(args.as_of_date)
    else:
        client.log("[2/6] 최근 영업일 탐색")
        as_of = find_latest_business_day(client)
        client.log(f"  └─ 기준일 확정: {as_of}")

    client.log("[3/6] KOSPI200 구성종목 조회")
    try:
        kospi200_tickers = client.get_kospi200_tickers(as_of)
        save_constituents_cache(paths, kospi200_tickers, as_of)
        client.log(f"  └─ 구성종목 수: {len(kospi200_tickers)}")
    except Exception as exc:
        cached = load_cached_constituents(paths)
        if not cached:
            raise
        kospi200_tickers = cached
        client.log(
            "  └─ pykrx 구성종목 조회 실패로 최신 캐시를 사용합니다: "
            f"{exc} / cached={len(kospi200_tickers)}"
        )

    client.log("[4/6] 전종목 시세 / fundamental 수집")
    ohlcv_raw = client.fetch_market_ohlcv(as_of, market="ALL")
    fundamental_raw = client.fetch_market_fundamental(as_of, market="ALL")
    client.log(f"  └─ OHLCV raw rows: {len(ohlcv_raw):,}")
    client.log(f"  └─ Fundamental raw rows: {len(fundamental_raw):,}")

    client.log("[5/6] KOSPI200 스냅샷 생성")
    snapshot_df = build_snapshot_dataframe(as_of, kospi200_tickers, ohlcv_raw, fundamental_raw)
    client.log(f"  └─ 최종 스냅샷 rows: {len(snapshot_df):,}")

    client.log("[6/6] 파일 저장 및 보존 정책 적용")
    saved = save_snapshot_files(snapshot_df, as_of, paths)
    deleted = prune_daily_snapshots(paths, keep_days=max(args.keep_daily, 1))

    print("\n완료")
    print(f"- 기준일: {as_of} ({yyyymmdd_to_iso(as_of)})")
    print(f"- 일별 CSV: {saved['daily_csv'].as_posix()}")
    print(f"- 일별 JSON: {saved['daily_json'].as_posix()}")
    print(f"- 최신 CSV: {saved['latest_csv'].as_posix()}")
    print(f"- 최신 JSON: {saved['latest_json'].as_posix()}")
    print(f"- 월별 CSV: {saved['monthly_csv'].as_posix()}")
    print(f"- 월별 JSON: {saved['monthly_json'].as_posix()}")
    print(f"- 매니페스트: {saved['manifest'].as_posix()}")
    print(f"- 정리된 일별 스냅샷 수: {len(deleted)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.", file=sys.stderr)
        raise SystemExit(130)

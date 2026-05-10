"""
dart_client.py
==============
차차기 W5 — DART Open API 클라이언트.

설계:
  - 인증: DART_API_KEY 환경변수 (https://opendart.fss.or.kr/ 발급, 무료).
  - 공시 *유형 코드* 위주 (`pblntf_ty`, `pblntf_detail_ty`) — 차차기 §절대 5
    "raw 텍스트 파싱 의존도 높이지 말 것" 준수.
  - rate limit 보호: 기본 0.2s/req (5 req/s, 일 10,000 호출 안전).
  - 404·429·5xx 재시도 (max 3회, 지수 backoff).

엔드포인트 (현 구현 — 공시검색):
  GET https://opendart.fss.or.kr/api/list.json
    params: crtfc_key, bgn_de, end_de, corp_code(optional), page_no, page_count(<=100)
    response: {status, message, page_no, page_count, total_count, total_page, list:[...]}
    list[i] keys: corp_code, corp_name, stock_code, rcept_no, rcept_dt, report_nm,
                  pblntf_ty, pblntf_detail_ty, flr_nm, rm

본 모듈의 *순수 함수* 는 단위 테스트 가능. HTTP 호출만 외부 의존.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

import requests


DART_BASE_URL = "https://opendart.fss.or.kr/api"
DEFAULT_RATE_LIMIT_SEC = 0.2          # 5 req/s
DEFAULT_TIMEOUT_SEC    = 10
DEFAULT_MAX_RETRIES    = 3
PAGE_SIZE_MAX          = 100


class DartError(RuntimeError):
    """DART API 호출 실패. message + status 보존."""

    def __init__(self, message: str, status: Optional[str] = None):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class DartConfig:
    api_key:        str
    rate_limit_sec: float = DEFAULT_RATE_LIMIT_SEC
    timeout_sec:    float = DEFAULT_TIMEOUT_SEC
    max_retries:    int   = DEFAULT_MAX_RETRIES

    @classmethod
    def from_env(cls) -> "DartConfig":
        key = os.getenv("DART_API_KEY")
        if not key:
            raise DartError("DART_API_KEY env var 미설정. https://opendart.fss.or.kr/ 발급 후 export.")
        return cls(api_key=key)


# ── 응답 status 검증 ────────────────────────────────────────────────────────

# DART status 코드 (https://opendart.fss.or.kr/guide/main.do):
#   "000": 정상
#   "010": 등록되지 않은 키
#   "011": 사용할 수 없는 키 (활성화 대기/만료)
#   "013": 조회된 데이터 없음
#   "020": 요청 횟수 초과
#   "100": 필드 오류
#   "800": 시스템 점검
DART_STATUS_OK     = "000"
DART_STATUS_NO_DATA = "013"
DART_STATUS_RATE_LIMITED = "020"


def _validate_status(payload: dict) -> dict:
    """status 검증. 정상·NoData → payload 그대로. 그 외 → DartError."""
    status = str(payload.get("status", ""))
    if status == DART_STATUS_OK:
        return payload
    if status == DART_STATUS_NO_DATA:
        # 빈 list 로 정규화 (caller 가 분기 안 해도 되도록).
        payload.setdefault("list", [])
        return payload
    raise DartError(
        f"DART API status={status} message={payload.get('message')!r}",
        status=status,
    )


# ── 핵심 GET (rate limit + retry) ──────────────────────────────────────────

def _get(
    path:    str,
    params:  dict,
    config:  DartConfig,
    *,
    session: Optional[requests.Session] = None,
) -> dict:
    sess = session or requests.Session()
    last_exc: Optional[Exception] = None
    for attempt in range(1, config.max_retries + 1):
        try:
            time.sleep(config.rate_limit_sec)
            r = sess.get(f"{DART_BASE_URL}/{path}", params=params,
                         timeout=config.timeout_sec)
        except requests.RequestException as e:
            last_exc = e
            time.sleep(0.5 * attempt)   # 단순 backoff
            continue
        if r.status_code == 200:
            try:
                payload = r.json()
            except ValueError as e:
                raise DartError(f"DART 응답 JSON 파싱 실패: {e}")
            return _validate_status(payload)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(0.5 * attempt)
            last_exc = DartError(f"DART HTTP {r.status_code}")
            continue
        raise DartError(f"DART HTTP {r.status_code}: {r.text[:200]}")
    raise DartError(f"DART 호출 {config.max_retries}회 재시도 실패: {last_exc}")


# ── 공시검색 ────────────────────────────────────────────────────────────────

def list_disclosures(
    *,
    config:    DartConfig,
    bgn_de:    str,                       # "YYYYMMDD"
    end_de:    str,
    corp_code: Optional[str] = None,      # 명시 시 한 회사만
    pblntf_ty: Optional[str] = None,      # 공시 유형 1차 (A/B/C/D/E/F/G/H/I/J)
    page_no:   int = 1,
    page_count: int = PAGE_SIZE_MAX,
    session:   Optional[requests.Session] = None,
) -> dict:
    params = {
        "crtfc_key": config.api_key,
        "bgn_de":    bgn_de,
        "end_de":    end_de,
        "page_no":   int(page_no),
        "page_count": min(int(page_count), PAGE_SIZE_MAX),
    }
    if corp_code:
        params["corp_code"] = corp_code
    if pblntf_ty:
        params["pblntf_ty"] = pblntf_ty
    payload = _get("list.json", params, config, session=session)
    # DART list.json 응답에는 pblntf_ty 가 없고 *검색 파라미터로만* 존재.
    # caller 가 유형 한정 호출했으면 응답 row 에 주입해 caller 편의.
    if pblntf_ty:
        for row in payload.get("list", []):
            row.setdefault("pblntf_ty", pblntf_ty)
    return payload


def iter_disclosures(
    *,
    config: DartConfig,
    bgn_de: str,
    end_de: str,
    pblntf_ty: Optional[str] = None,
    session:    Optional[requests.Session] = None,
) -> Iterator[dict]:
    """공시검색 전체 페이지를 순회. 행 단위 yield.
    *주의*: 큰 기간 (월·연 단위) 호출 시 일별로 쪼개 부르는 것이 안정적.
    """
    sess = session or requests.Session()
    page_no = 1
    total_page = 1
    while page_no <= total_page:
        payload = list_disclosures(
            config=config, bgn_de=bgn_de, end_de=end_de,
            pblntf_ty=pblntf_ty, page_no=page_no, session=sess,
        )
        for row in payload.get("list", []):
            yield row
        # NoData (013) 또는 빈 list → 종료.
        new_total_page = int(payload.get("total_page") or 1)
        if not payload.get("list"):
            return
        total_page = new_total_page
        page_no += 1


# ── 공시 유형 코드 매핑 (참조용 상수) ───────────────────────────────────────

PBLNTF_TY_CODES: dict[str, str] = {
    "A": "정기공시",
    "B": "주요사항보고",
    "C": "발행공시",
    "D": "지분공시",
    "E": "기타공시",
    "F": "외부감사관련",
    "G": "펀드공시",
    "H": "자산유동화",
    "I": "거래소공시",
    "J": "공정위공시",
}

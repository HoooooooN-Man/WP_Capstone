"""
services/data.py
================
Tier 1B 4.5 (CLAUDE.md §3.0) — `data.py` 는 6개 도메인 모듈로 분할되었다.

본 파일은 **thin re-export shim** 으로, 라우터의 기존 임포트 패턴
`from ..services import data as svc` 를 깨지 않기 위해 모든 공개 함수를
도메인 모듈에서 그대로 노출한다.

도메인 모듈:
  - scores_svc.py  : 추천·이력·섹터·검색·스크리너·비교·레짐·KOSPI200 포트폴리오
  - charts_svc.py  : 차트·현재가·급상승
  - finance_svc.py : 재무 이력·최신 분기
  - backtest_svc.py: 백테스트 월별·요약·커스텀
  - news_svc.py    : 뉴스 피드·상세
  - metrics_svc.py : 모델 모니터링 지표

신규 코드는 도메인 모듈을 직접 import 하기를 권장:
  from .scores_svc import get_recommendations
  from .metrics_svc import get_model_metrics

기존 코드는 다음 패턴으로 계속 동작:
  from ..services import data as svc
  svc.get_recommendations(...)
"""

from __future__ import annotations

# ── 공유 인프라 (역시 _core 에서 노출되어야 import 호환) ──────────────────────
from ._core import (
    init_duckdb,
    con as _con,
    news_con as _news_con,
    cached as _cached,
    cache_key as _cache_key,
    get_redis as _get_redis,
    resolve_version as _resolve_version,
    get_available_dates,
    get_available_versions,
)

# ── 도메인 함수 re-export ────────────────────────────────────────────────────
from .scores_svc import (
    get_recommendations,
    get_stock_history,
    get_sector_summary,
    search_stocks,
    screen_stocks,
    compare_stocks,
    get_market_regime,
    get_kospi200_portfolio,
)
# Private 심볼은 *모듈 내부 호환*용으로만 import (외부 호출 없음 확인됨, 캡스톤 정리).
# 향후 누가 `from ..services.data import _get_kospi_regime` 같이 쓰면 깨질 수 있으므로
# 발견 시 직접 scores_svc 에서 import 하도록 유도.
from .charts_svc import (
    get_chart,
    get_stock_price,
    get_rising_stocks,
)
from .finance_svc import (
    get_finance,
    get_finance_latest,
)
from .backtest_svc import (
    get_backtest_monthly_returns,
    get_backtest_summary,
    run_custom_backtest,
)
from .news_svc import (
    get_news_feed,
    get_news_detail,
)
from .metrics_svc import (
    get_model_metrics,
)


__all__ = [
    # 공유 인프라
    "init_duckdb",
    "_con",
    "_news_con",
    "_cached",
    "_cache_key",
    "_get_redis",
    "_resolve_version",
    "get_available_dates",
    "get_available_versions",
    # 도메인 함수
    "get_recommendations",
    "get_stock_history",
    "get_sector_summary",
    "search_stocks",
    "screen_stocks",
    "compare_stocks",
    "get_market_regime",
    "get_kospi200_portfolio",
    "get_chart",
    "get_stock_price",
    "get_rising_stocks",
    "get_finance",
    "get_finance_latest",
    "get_backtest_monthly_returns",
    "get_backtest_summary",
    "run_custom_backtest",
    "get_news_feed",
    "get_news_detail",
    "get_model_metrics",
]

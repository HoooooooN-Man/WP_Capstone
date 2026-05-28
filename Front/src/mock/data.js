/**
 * ──────────────────────────────────────────────
 *  MOCK DATA  (임시 데이터)
 *  MOCK_USER / MOCK_FEEDS / MOCK_COMPANIES / MOCK_PORTFOLIOS 제거됨
 *  아래 generateMockOHLC 만 CompanyView 차트에서 사용 중
 * ──────────────────────────────────────────────
 */

// ── 주가 임시 OHLCV 데이터 생성 ──────────────
// [API] GET /api/stocks/{ticker}/ohlcv?from=&to= 로 교체
// ticker 문자열을 seed로 사용해 결정론적 랜덤 데이터 생성 → 새로고침해도 동일한 차트
export function generateMockOHLC(ticker, currentPrice) {
  let seed = ticker.split('').reduce((acc, c) => acc * 31 + c.charCodeAt(0), 1);
  const rng = () => {
    seed = (seed * 1664525 + 1013904223) & 0x7fffffff;
    return seed / 0x7fffffff;
  };

  const DAYS = 252; // 약 1년치 거래일
  const data = [];
  let price = currentPrice * (0.72 + rng() * 0.56); // 시작가: 현재가 대비 ±28% 내
  let trend = (rng() - 0.5) * 0.002;

  for (let i = 0; i < DAYS; i++) {
    if (rng() < 0.06) trend = (rng() - 0.5) * 0.003; // 추세 전환
    const dayChange    = trend + (rng() - 0.5) * 0.028;
    const intraVol     = rng() * 0.013;
    const open         = price;
    const close        = price * (1 + dayChange);
    const high         = Math.max(open, close) * (1 + intraVol);
    const low          = Math.min(open, close) * (1 - intraVol * 0.8);
    const volume       = Math.floor((rng() * 1200000 + 250000) * (1 + Math.abs(dayChange) * 8));
    const date         = new Date(Date.now() - (DAYS - 1 - i) * 86400000);
    data.push({ date, open, high, low, close, volume });
    price = close;
  }

  // 마지막 종가 → 실제 현재가로 스케일 보정
  const scale = currentPrice / data[data.length - 1].close;
  return data.map(d => ({
    date:   d.date,
    open:   Math.round(d.open  * scale),
    high:   Math.round(d.high  * scale),
    low:    Math.round(d.low   * scale),
    close:  Math.round(d.close * scale),
    volume: d.volume,
  }));
}


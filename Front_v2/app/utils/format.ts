/**
 * 가격·숫자 포맷팅 유틸 — PRD §1.7 정합.
 *
 * 모든 페이지에서 일관된 한국식 포맷을 위한 공통 함수.
 */

export function formatPrice(p: number | null | undefined, withUnit: boolean = false): string {
  if (p == null || !Number.isFinite(p)) return '—';
  const formatted = p.toLocaleString('ko-KR');
  return withUnit ? `${formatted}원` : formatted;
}

export function formatPercent(p: number | null | undefined, digits: number = 2): string {
  if (p == null || !Number.isFinite(p)) return '—';
  return `${p >= 0 ? '+' : ''}${p.toFixed(digits)}%`;
}

export function formatScore(s: number | null | undefined): string {
  if (s == null || !Number.isFinite(s)) return '—';
  return s.toFixed(1);
}

/** 큰 수 한글 단위 (만/억/조). 예: 1,234,567,890,000 → "1.23조" */
export function formatLargeNumber(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—';
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${(n / 1e12).toFixed(2)}조`;
  if (abs >= 1e8)  return `${(n / 1e8).toFixed(1)}억`;
  if (abs >= 1e4)  return `${Math.round(n / 1e4).toLocaleString('ko-KR')}만`;
  return n.toLocaleString('ko-KR');
}

/** 시가총액 라벨 — 원 단위 입력. 예: 5_420_000_000_000 → "542조" */
export function formatMarketCap(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—';
  return formatLargeNumber(n);
}

/**
 * 수익률 색상 (CSS 변수) — 양수=up / 음수=down / null=down (안전).
 * 5+ 페이지 중복 패턴 통일 (StockListRow / WinnerCard / SignalPage / SmartScorePage / ComparePage).
 */
export function getReturnColor(value: number | null | undefined): string {
  return value != null && value >= 0 ? 'var(--color-up)' : 'var(--color-down)';
}

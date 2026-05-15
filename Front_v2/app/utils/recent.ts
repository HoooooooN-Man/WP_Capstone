/**
 * 최근 본 종목 — localStorage 기반.
 * StockDetailPage 진입 시 pushRecentStock 으로 기록하고,
 * ContextRail "최근 본 종목" 에서 loadRecentStocks 로 노출한다.
 */

const KEY = 'recent-stocks';
const MAX = 8;

export interface RecentStock {
  ticker: string;
  name: string;
}

export function loadRecentStocks(): RecentStock[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function pushRecentStock(stock: RecentStock) {
  if (!stock || !stock.ticker) return;
  try {
    const rest = loadRecentStocks().filter((s) => s.ticker !== stock.ticker);
    const next = [{ ticker: stock.ticker, name: stock.name || stock.ticker }, ...rest].slice(0, MAX);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* ignore — localStorage 비가용 환경 */
  }
}

/**
 * api/watchlist.ts
 * ================
 * Tier 1.6 (PRD §2.1) — 관심종목 서버 동기화 API 클라이언트.
 * 인증·커뮤니티 서버(:8000)의 /users/me/watchlist CRUD 를 호출.
 *
 * 사용:
 *   import { listWatchlist, addWatchlist, removeWatchlist, migrateWatchlist } from '@/api/watchlist'
 */
import dbapi from './dbapi'

export interface WatchlistEntry {
  ticker: string
  added_at: string
}

export interface WatchlistResponse {
  total: number
  items: WatchlistEntry[]
}

export async function listWatchlist(): Promise<WatchlistResponse> {
  const r = await dbapi.get<WatchlistResponse>('/users/me/watchlist')
  return r.data
}

export async function addWatchlist(ticker: string): Promise<WatchlistEntry> {
  const r = await dbapi.post<WatchlistEntry>('/users/me/watchlist', { ticker })
  return r.data
}

export async function removeWatchlist(ticker: string): Promise<void> {
  await dbapi.delete(`/users/me/watchlist/${encodeURIComponent(ticker)}`)
}

/**
 * localStorage 의 watchlist 배열을 서버로 일괄 이관 (1회용).
 * 비로그인 시절 쌓인 관심종목을 로그인 직후 한 번 호출하면 된다.
 */
export async function migrateWatchlist(tickers: string[]): Promise<WatchlistResponse> {
  const r = await dbapi.post<WatchlistResponse>('/users/me/watchlist/migrate', { tickers })
  return r.data
}

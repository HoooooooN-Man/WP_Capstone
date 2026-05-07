/**
 * stores/watchlist.ts
 * ===================
 * Tier 1.6 (PRD §2.1) + Tier 2.4 (TS 마이그레이션).
 *
 * 동작 원칙:
 *   - 로그인 상태: 서버(/users/me/watchlist) 가 source of truth, 로컬은 캐시.
 *   - 비로그인  : localStorage 가 source of truth (기존 동작 유지).
 *   - 로그인 직후 1회: localStorage 에 쌓인 ticker 들을 서버로 마이그레이션 후
 *                     localStorage 비움 (capstone §2.1: 데이터 유실 방지).
 *
 * 침묵 실패 금지 (Tier 1.7 §3.2): 서버 호출 에러는 console.error 로 남기고,
 * 가능한 경우 localStorage fallback 으로 계속 동작.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import {
  listWatchlist as apiList,
  addWatchlist as apiAdd,
  removeWatchlist as apiRemove,
  migrateWatchlist as apiMigrate,
} from '@/api/watchlist'

const LS_KEY = 'watchlist'
const LS_MIGRATED_KEY = 'watchlist_migrated_v1'   // 마이그레이션 완료 플래그

function _loadLocal(): string[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((t) => typeof t === 'string') : []
  } catch (e) {
    console.error('[watchlist] failed to parse localStorage', e)
    return []
  }
}

function _saveLocal(tickers: string[]): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(tickers))
  } catch (e) {
    console.error('[watchlist] failed to persist localStorage', e)
  }
}

export const useWatchlistStore = defineStore('watchlist', () => {
  const tickers = ref<string[]>([])
  const isAuthenticated = ref(false)
  const isSyncing = ref(false)
  const lastError = ref<string | null>(null)

  const isFavorite = computed(() => (ticker: string): boolean =>
    tickers.value.includes(ticker),
  )

  /** 비로그인 → 로그인 전환 시 호출. localStorage 잔류분을 서버로 일괄 이관. */
  async function migrateOnLogin(): Promise<void> {
    if (localStorage.getItem(LS_MIGRATED_KEY) === '1') return
    const local = _loadLocal()
    if (local.length === 0) {
      localStorage.setItem(LS_MIGRATED_KEY, '1')
      return
    }
    try {
      const res = await apiMigrate(local)
      tickers.value = res.items.map((it) => it.ticker)
      // 성공한 경우에만 localStorage 비우고 플래그 set.
      localStorage.removeItem(LS_KEY)
      localStorage.setItem(LS_MIGRATED_KEY, '1')
    } catch (e) {
      console.error('[watchlist] migration failed; keeping localStorage', e)
      lastError.value = '관심종목 동기화 실패 (로컬에 보관)'
    }
  }

  /** 로그인 직후 또는 앱 부팅 시 호출. 서버 우선, 실패 시 localStorage. */
  async function fetchWatchlist(authenticated = false): Promise<void> {
    isAuthenticated.value = authenticated
    isSyncing.value = true
    lastError.value = null
    try {
      if (authenticated) {
        await migrateOnLogin()
        const res = await apiList()
        tickers.value = res.items.map((it) => it.ticker)
        return
      }
      tickers.value = _loadLocal()
    } catch (e: any) {
      console.error('[watchlist] fetch failed; falling back to localStorage', e)
      lastError.value = '관심종목 불러오기 실패'
      tickers.value = _loadLocal()
    } finally {
      isSyncing.value = false
    }
  }

  async function addTicker(ticker: string): Promise<void> {
    if (!ticker || tickers.value.includes(ticker)) return
    // optimistic UI: 즉시 반영.
    tickers.value = [...tickers.value, ticker]

    if (isAuthenticated.value) {
      try {
        await apiAdd(ticker)
      } catch (e) {
        console.error('[watchlist] add failed, rolling back', e)
        tickers.value = tickers.value.filter((t) => t !== ticker)
        lastError.value = '관심종목 추가 실패'
        throw e
      }
    } else {
      _saveLocal(tickers.value)
    }
  }

  async function removeTicker(ticker: string): Promise<void> {
    if (!tickers.value.includes(ticker)) return
    const before = [...tickers.value]
    tickers.value = tickers.value.filter((t) => t !== ticker)

    if (isAuthenticated.value) {
      try {
        await apiRemove(ticker)
      } catch (e) {
        console.error('[watchlist] remove failed, rolling back', e)
        tickers.value = before
        lastError.value = '관심종목 삭제 실패'
        throw e
      }
    } else {
      _saveLocal(tickers.value)
    }
  }

  async function toggleTicker(ticker: string): Promise<void> {
    if (tickers.value.includes(ticker)) {
      await removeTicker(ticker)
    } else {
      await addTicker(ticker)
    }
  }

  return {
    tickers,
    isAuthenticated,
    isSyncing,
    lastError,
    isFavorite,
    fetchWatchlist,
    addTicker,
    removeTicker,
    toggleTicker,
    migrateOnLogin,
  }
})

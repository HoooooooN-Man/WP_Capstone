// UX W5 — Watchlist composable. 기존 Pinia store wrapper.
// 결정: 권고 수용 — Pinia 유지 (이미 적재 자산), 낙관 업데이트 + Undo toast.
// caller 가 toast 표시 책임 (toast 시스템 없어 stub interface).

import { computed, ref, type Ref } from 'vue'

export interface WatchlistItemMin {
  ticker: string
  name?: string
  sector?: string
}

export interface PendingRemoval {
  ticker: string
  removedAt: number      // timestamp ms
  expireMs: number       // Undo 가능 기간 (5000)
}

// caller (View) 가 store 의 ref·메서드를 주입.
// 본 composable 은 *순수 함수형 wrapper* — 테스트 가능.
export interface WatchlistStoreLike {
  tickers: Ref<string[]> | { value: string[] }
  toggle?:   (ticker: string) => void | Promise<void>
  remove?:   (ticker: string) => void | Promise<void>
  restore?:  (ticker: string) => void | Promise<void>
}

export function useWatchlist(store: WatchlistStoreLike) {
  // 낙관 제거를 위한 pending 큐 (Undo 가능).
  const pending = ref<PendingRemoval[]>([])

  function isPending(ticker: string): boolean {
    const now = Date.now()
    return pending.value.some(p =>
      p.ticker === ticker && (now - p.removedAt) < p.expireMs
    )
  }

  function visibleTickers(): string[] {
    const raw = (store.tickers as any).value ?? store.tickers ?? []
    return raw.filter((t: string) => !isPending(t))
  }

  function removeWithUndo(ticker: string, expireMs = 5000): PendingRemoval {
    const entry: PendingRemoval = { ticker, removedAt: Date.now(), expireMs }
    pending.value.push(entry)
    // 낙관: store 에 즉시 알림 (실 API 호출 위임)
    store.remove?.(ticker)
    // 만료 시 큐에서 자동 제거 (caller toast 가 만료 시 호출, 또는 timer)
    setTimeout(() => {
      pending.value = pending.value.filter(p => p !== entry)
    }, expireMs + 100)
    return entry
  }

  function undoRemove(ticker: string): boolean {
    const entry = pending.value.find(p => p.ticker === ticker)
    if (!entry) return false
    pending.value = pending.value.filter(p => p !== entry)
    store.restore?.(ticker) ?? store.toggle?.(ticker)
    return true
  }

  return {
    visibleTickers: computed(() => visibleTickers()),
    pending:        computed(() => pending.value),
    isPending,
    removeWithUndo,
    undoRemove,
  }
}

// 정렬 옵션 (View 가 사용).
export type SortKey = 'recent' | 'name' | 'score' | 'change'

export function sortTickers<T extends { ticker: string; name?: string; score?: number; changePercent?: number }>(
  items: T[],
  key:   SortKey,
): T[] {
  const arr = [...items]
  switch (key) {
    case 'name':
      return arr.sort((a, b) => (a.name ?? a.ticker).localeCompare(b.name ?? b.ticker, 'ko'))
    case 'score':
      return arr.sort((a, b) => (b.score ?? -Infinity) - (a.score ?? -Infinity))
    case 'change':
      return arr.sort((a, b) => (b.changePercent ?? -Infinity) - (a.changePercent ?? -Infinity))
    case 'recent':
    default:
      return arr   // 추가 순서 그대로 (caller 가 등록 순으로 store 에 유지)
  }
}

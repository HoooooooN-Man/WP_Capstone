import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { useWatchlist, sortTickers } from '@/composables/useWatchlist'

describe('useWatchlist', () => {
  function makeStore(initial: string[] = []) {
    return {
      tickers: ref(initial),
      remove:  vi.fn(),
      restore: vi.fn(),
      toggle:  vi.fn(),
    }
  }

  it('visibleTickers — pending 제외', () => {
    const store = makeStore(['A', 'B', 'C'])
    const { visibleTickers, removeWithUndo } = useWatchlist(store)
    expect(visibleTickers.value).toEqual(['A', 'B', 'C'])
    removeWithUndo('B')
    expect(visibleTickers.value).toEqual(['A', 'C'])
  })

  it('removeWithUndo — store.remove 호출 + pending 등록', () => {
    const store = makeStore(['A'])
    const { removeWithUndo, isPending } = useWatchlist(store)
    removeWithUndo('A')
    expect(store.remove).toHaveBeenCalledWith('A')
    expect(isPending('A')).toBe(true)
  })

  it('undoRemove — pending 제거 + store.restore 또는 toggle', () => {
    const store = makeStore(['A'])
    const { removeWithUndo, undoRemove, isPending } = useWatchlist(store)
    removeWithUndo('A')
    const ok = undoRemove('A')
    expect(ok).toBe(true)
    expect(isPending('A')).toBe(false)
    expect(store.restore).toHaveBeenCalledWith('A')
  })

  it('undoRemove — pending 없으면 false', () => {
    const store = makeStore()
    const { undoRemove } = useWatchlist(store)
    expect(undoRemove('X')).toBe(false)
  })

  it('만료 후 pending 자동 제거', async () => {
    vi.useFakeTimers()
    const store = makeStore(['A'])
    const { removeWithUndo, isPending } = useWatchlist(store)
    removeWithUndo('A', 100)
    expect(isPending('A')).toBe(true)
    vi.advanceTimersByTime(200)
    expect(isPending('A')).toBe(false)
    vi.useRealTimers()
  })
})

describe('sortTickers', () => {
  const items = [
    { ticker: '005930', name: '삼성전자',   score: 87, changePercent: 1.2 },
    { ticker: '000660', name: 'SK하이닉스', score: 85, changePercent: -0.5 },
    { ticker: '035420', name: 'NAVER',      score: 82, changePercent: 2.1 },
  ]

  it('recent — 원래 순서 유지', () => {
    const sorted = sortTickers(items, 'recent')
    expect(sorted.map(i => i.ticker)).toEqual(['005930', '000660', '035420'])
  })

  it('name — 한국어 가나다순 (localeCompare ko)', () => {
    // 한글끼리 가나다순 검증 (영문 vs 한글 순서는 환경 의존).
    const koItems = [
      { ticker: 'X', name: '삼성전자' },
      { ticker: 'Y', name: '네이버' },
      { ticker: 'Z', name: 'LG화학' },
    ]
    const sorted = sortTickers(koItems, 'name')
    // localeCompare ko: 네이버 < 삼성전자 (한글 가나다)
    const koSorted = sorted.filter(s => /^[가-힣]/.test(s.name))
    expect(koSorted.map(s => s.name)).toEqual(['네이버', '삼성전자'])
  })

  it('score — 높은 순', () => {
    const sorted = sortTickers(items, 'score')
    expect(sorted.map(i => i.score)).toEqual([87, 85, 82])
  })

  it('change — 등락률 높은 순', () => {
    const sorted = sortTickers(items, 'change')
    expect(sorted[0].changePercent).toBe(2.1)
    expect(sorted[2].changePercent).toBe(-0.5)
  })

  it('빈 배열 graceful', () => {
    expect(sortTickers([], 'name')).toEqual([])
  })

  it('원본 배열 mutate 안 함', () => {
    const original = [...items]
    sortTickers(items, 'score')
    expect(items).toEqual(original)
  })
})

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WatchlistItem from '@/components/WatchlistItem.vue'

describe('WatchlistItem', () => {
  it('ticker·name 표시', () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자' },
    })
    expect(w.text()).toContain('005930')
    expect(w.text()).toContain('삼성전자')
  })

  it('price 천 단위', () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자', price: 70500 },
    })
    expect(w.text()).toContain('70,500')
  })

  it('상승 ▲ + up 클래스', () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자', changePercent: 1.5 },
    })
    expect(w.find('.watchlist-item__change--up').exists()).toBe(true)
    expect(w.text()).toContain('▲')
  })

  it('하락 ▼ + down 클래스', () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자', changePercent: -1.5 },
    })
    expect(w.find('.watchlist-item__change--down').exists()).toBe(true)
    expect(w.text()).toContain('▼')
  })

  it('price·changePercent 부재 graceful', () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자' },
    })
    expect(w.find('.watchlist-item__price').exists()).toBe(false)
    expect(w.find('.watchlist-item__change').exists()).toBe(false)
  })

  it('카드 클릭 → click emit', async () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자' },
    })
    await w.trigger('click')
    expect(w.emitted('click')).toBeTruthy()
  })

  it('제거 버튼 → remove emit, 카드 click 안 옴 (stopPropagation)', async () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자' },
    })
    await w.find('.watchlist-item__remove').trigger('click')
    expect(w.emitted('remove')).toBeTruthy()
    expect(w.emitted('click')).toBeFalsy()
  })

  it('제거 버튼 aria-label 종목명 포함', () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자' },
    })
    const btn = w.find('.watchlist-item__remove')
    expect(btn.attributes('aria-label')).toContain('삼성전자')
    expect(btn.attributes('aria-label')).toContain('제거')
  })

  it('sector 표시 (선택)', () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자', sector: 'IT' },
    })
    expect(w.text()).toContain('IT')
  })

  it('keyboard Enter → click emit', async () => {
    const w = mount(WatchlistItem, {
      props: { ticker: '005930', name: '삼성전자' },
    })
    await w.trigger('keydown.enter')
    expect(w.emitted('click')).toBeTruthy()
  })
})

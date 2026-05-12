import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StockCard from '@/components/StockCard.vue'

describe('StockCard', () => {
  it('기본 ticker·name 표시', () => {
    const w = mount(StockCard, { props: { ticker: '005930', name: '삼성전자' } })
    expect(w.text()).toContain('005930')
    expect(w.text()).toContain('삼성전자')
  })

  it('price 천 단위 구분', () => {
    const w = mount(StockCard, { props: { ticker: '005930', name: '삼성전자', price: 70500 } })
    expect(w.text()).toContain('70,500')
  })

  it('상승 → 빨강 (up) 클래스 + 삼각형 ▲', () => {
    const w = mount(StockCard, {
      props: { ticker: '005930', name: '삼성전자', price: 70500, changePercent: 1.25 },
    })
    expect(w.find('.stock-card__change--up').exists()).toBe(true)
    expect(w.text()).toContain('▲')
    expect(w.text()).toContain('1.25%')
  })

  it('하락 → 파랑 (down) 클래스 + ▼', () => {
    const w = mount(StockCard, {
      props: { ticker: '005930', name: '삼성전자', changePercent: -2.5 },
    })
    expect(w.find('.stock-card__change--down').exists()).toBe(true)
    expect(w.text()).toContain('▼')
  })

  it('등락률 0 → 부호 없음 (-)', () => {
    const w = mount(StockCard, {
      props: { ticker: '005930', name: '삼성전자', changePercent: 0 },
    })
    expect(w.find('.stock-card__change--up').exists()).toBe(false)
    expect(w.find('.stock-card__change--down').exists()).toBe(false)
    expect(w.text()).toContain('-')
  })

  it('price 부재 graceful', () => {
    const w = mount(StockCard, { props: { ticker: '005930', name: '삼성전자' } })
    expect(w.find('.stock-card__price').exists()).toBe(false)
  })

  it('changePercent 부재 graceful', () => {
    const w = mount(StockCard, { props: { ticker: '005930', name: '삼성전자', price: 70500 } })
    expect(w.find('.stock-card__change').exists()).toBe(false)
  })

  it('tier·score 부재 시 둘 다 미표시', () => {
    const w = mount(StockCard, { props: { ticker: '005930', name: '삼성전자' } })
    expect(w.find('.stock-card__tier').exists()).toBe(false)
    expect(w.find('.stock-card__score').exists()).toBe(false)
  })

  it('tier·score 표시', () => {
    const w = mount(StockCard, {
      props: { ticker: '005930', name: '삼성전자', tier: 'A', score: 87 },
    })
    expect(w.find('.stock-card__tier').text()).toBe('A')
    expect(w.text()).toContain('87점')
  })

  it('sector 표시 (선택)', () => {
    const w = mount(StockCard, {
      props: { ticker: '005930', name: '삼성전자', sector: 'IT' },
    })
    expect(w.text()).toContain('IT')
  })

  it('클릭 시 click 이벤트 emit', async () => {
    const w = mount(StockCard, { props: { ticker: '005930', name: '삼성전자' } })
    await w.trigger('click')
    expect(w.emitted('click')).toBeTruthy()
  })

  it('keyboard Enter → click emit', async () => {
    const w = mount(StockCard, { props: { ticker: '005930', name: '삼성전자' } })
    await w.trigger('keydown.enter')
    expect(w.emitted('click')).toBeTruthy()
  })
})

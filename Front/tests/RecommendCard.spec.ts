import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RecommendCard from '@/components/RecommendCard.vue'

const base = {
  ticker: '005930',
  name: '삼성전자',
  sector: 'IT',
  score: 87,
  tier: 'A' as const,
}

describe('RecommendCard', () => {
  it('기본 props 렌더', () => {
    const w = mount(RecommendCard, { props: base })
    expect(w.text()).toContain('005930')
    expect(w.text()).toContain('삼성전자')
    expect(w.text()).toContain('IT')
    expect(w.text()).toContain('87')
    expect(w.find('.recommend-card__tier').text()).toBe('A')
  })

  it('rank 표시 (선택)', () => {
    const w = mount(RecommendCard, { props: { ...base, rank: 3 } })
    expect(w.text()).toContain('#3')
  })

  it('rank 부재 시 미표시', () => {
    const w = mount(RecommendCard, { props: base })
    expect(w.find('.recommend-card__rank').exists()).toBe(false)
  })

  it('sector 부재 graceful', () => {
    const { sector, ...noSector } = base
    const w = mount(RecommendCard, { props: noSector })
    expect(w.find('.recommend-card__sector').exists()).toBe(false)
  })

  it('cohortMatch 한국어 매핑', () => {
    const w = mount(RecommendCard, { props: { ...base, cohortMatch: 'balanced' } })
    expect(w.text()).toContain('균형')
  })

  it('diversify 한국어 매핑', () => {
    const w = mount(RecommendCard, { props: { ...base, diversify: 'correlation' } })
    expect(w.text()).toContain('상관')
  })

  it('cohortMatch·diversify 없으면 footer 미표시', () => {
    const w = mount(RecommendCard, { props: base })
    expect(w.find('.recommend-card__footer').exists()).toBe(false)
  })

  it('isWatched=true 시 fill 아이콘', () => {
    const w = mount(RecommendCard, { props: { ...base, isWatched: true } })
    expect(w.find('.recommend-card__watch.is-watched').exists()).toBe(true)
    expect(w.find('.pi-bookmark-fill').exists()).toBe(true)
  })

  it('isWatched=false 시 빈 북마크 아이콘', () => {
    const w = mount(RecommendCard, { props: { ...base, isWatched: false } })
    expect(w.find('.pi-bookmark').exists()).toBe(true)
    expect(w.find('.pi-bookmark-fill').exists()).toBe(false)
  })

  it('클릭 시 click 이벤트 emit', async () => {
    const w = mount(RecommendCard, { props: base })
    await w.trigger('click')
    expect(w.emitted('click')).toBeTruthy()
  })

  it('북마크 버튼 클릭 시 watch-toggle 이벤트, 카드 click 은 안 옴 (stopPropagation)', async () => {
    const w = mount(RecommendCard, { props: base })
    await w.find('.recommend-card__watch').trigger('click')
    expect(w.emitted('watch-toggle')).toBeTruthy()
    expect(w.emitted('click')).toBeFalsy()
  })

  it('tier 모든 값 (A/B/C/D) data-tier 반영', () => {
    for (const t of ['A', 'B', 'C', 'D'] as const) {
      const w = mount(RecommendCard, { props: { ...base, tier: t } })
      expect(w.find('.recommend-card__tier').attributes('data-tier')).toBe(t)
    }
  })

  it('keyboard Enter → click emit', async () => {
    const w = mount(RecommendCard, { props: base })
    await w.trigger('keydown.enter')
    expect(w.emitted('click')).toBeTruthy()
  })
})

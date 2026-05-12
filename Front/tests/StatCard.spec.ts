import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatCard from '@/components/StatCard.vue'

describe('StatCard', () => {
  it('label·value 표시', () => {
    const w = mount(StatCard, { props: { label: '관심종목 수', value: 12 } })
    expect(w.text()).toContain('12')
    expect(w.text()).toContain('관심종목 수')
  })

  it('value=null → "-"', () => {
    const w = mount(StatCard, { props: { label: '추천 조회', value: null } })
    expect(w.text()).toContain('-')
    expect(w.text()).toContain('추천 조회')
  })

  it('value=undefined → "-"', () => {
    const w = mount(StatCard, { props: { label: '관심종목', value: undefined } })
    expect(w.text()).toContain('-')
  })

  it('value="" → "-"', () => {
    const w = mount(StatCard, { props: { label: '가입일', value: '' } })
    expect(w.text()).toContain('-')
  })

  it('suffix 표시', () => {
    const w = mount(StatCard, { props: { label: '수익률', value: 5.2, suffix: '%' } })
    expect(w.text()).toContain('5.2%')
  })

  it('value=0 → "0" (truthy 분기 회피)', () => {
    const w = mount(StatCard, { props: { label: '시도', value: 0 } })
    expect(w.text()).toContain('0')
    expect(w.text()).not.toContain('-')
  })

  it('value=string 표시', () => {
    const w = mount(StatCard, { props: { label: '가입일', value: '2026.03' } })
    expect(w.text()).toContain('2026.03')
  })
})

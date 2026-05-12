import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CohortCard from '@/components/CohortCard.vue'

describe('CohortCard', () => {
  it('balanced cohort label·description 표시', () => {
    const w = mount(CohortCard, { props: { cohort: 'balanced' } })
    expect(w.text()).toContain('균형')
    expect(w.text()).toContain('안정')
  })

  it('5 cohort 모두 한국어 라벨', () => {
    const expected: Record<string, string> = {
      balanced: '균형', growth: '성장', dividend: '배당',
      short_term: '단타', beginner: '입문',
    }
    for (const [key, label] of Object.entries(expected)) {
      const w = mount(CohortCard, { props: { cohort: key } })
      expect(w.text()).toContain(label)
    }
  })

  it('null cohort → empty state + 설정하기 버튼', () => {
    const w = mount(CohortCard, { props: { cohort: null } })
    expect(w.text()).toContain('관심사가 설정되지 않았습니다')
    expect(w.text()).toContain('설정하기')
  })

  it('알 수 없는 cohort → empty state (graceful)', () => {
    const w = mount(CohortCard, { props: { cohort: 'unknown_cohort' } })
    expect(w.text()).toContain('관심사가 설정되지 않았습니다')
  })

  it('변경 버튼 클릭 시 change 이벤트', async () => {
    const w = mount(CohortCard, { props: { cohort: 'balanced' } })
    await w.find('.cohort-card__change').trigger('click')
    expect(w.emitted('change')).toBeTruthy()
  })

  it('showChangeButton=false 시 버튼 숨김', () => {
    const w = mount(CohortCard, {
      props: { cohort: 'balanced', showChangeButton: false },
    })
    expect(w.find('.cohort-card__change').exists()).toBe(false)
  })
})

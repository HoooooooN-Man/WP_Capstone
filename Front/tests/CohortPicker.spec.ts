import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CohortPicker from '@/components/CohortPicker.vue'

describe('CohortPicker', () => {
  it('5 옵션 모두 렌더', () => {
    const w = mount(CohortPicker, { props: { modelValue: null } })
    const options = w.findAll('.cohort-picker__option')
    expect(options).toHaveLength(5)
    const text = w.text()
    expect(text).toContain('균형')
    expect(text).toContain('성장')
    expect(text).toContain('배당')
    expect(text).toContain('단타')
    expect(text).toContain('입문')
  })

  it('modelValue 매칭 시 is-selected 클래스', () => {
    const w = mount(CohortPicker, { props: { modelValue: 'growth' } })
    const selected = w.findAll('.is-selected')
    expect(selected).toHaveLength(1)
    expect(selected[0].text()).toContain('성장')
  })

  it('null modelValue → 선택 없음', () => {
    const w = mount(CohortPicker, { props: { modelValue: null } })
    expect(w.findAll('.is-selected')).toHaveLength(0)
  })

  it('option 클릭 → update:modelValue emit', async () => {
    const w = mount(CohortPicker, { props: { modelValue: null } })
    await w.findAll('input[type="radio"]')[1].setValue() // growth
    const events = w.emitted('update:modelValue')
    expect(events).toBeTruthy()
    expect(events?.[0]).toEqual(['growth'])
  })

  it('name prop 으로 radio group 이름 변경', () => {
    const w = mount(CohortPicker, {
      props: { modelValue: null, name: 'onboarding_cohort' },
    })
    const radios = w.findAll('input[type="radio"]')
    expect(radios[0].attributes('name')).toBe('onboarding_cohort')
  })

  it('legend 접근성 — "관심사 선택"', () => {
    const w = mount(CohortPicker, { props: { modelValue: null } })
    expect(w.find('legend').text()).toBe('관심사 선택')
  })
})

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MetaBadge from '@/components/MetaBadge.vue'

describe('MetaBadge', () => {
  it('label·value 표시', () => {
    const w = mount(MetaBadge, { props: { label: '모델', value: 'v11a_prime' } })
    expect(w.text()).toContain('모델')
    expect(w.text()).toContain('v11a_prime')
  })

  it('value=null → 렌더링 안 함 (graceful)', () => {
    const w = mount(MetaBadge, { props: { label: '모델', value: null } })
    expect(w.find('.meta-badge').exists()).toBe(false)
  })

  it('value=undefined → 렌더링 안 함', () => {
    const w = mount(MetaBadge, { props: { label: '모델', value: undefined } })
    expect(w.find('.meta-badge').exists()).toBe(false)
  })

  it('value="" → 렌더링 안 함 (빈 문자열 graceful)', () => {
    const w = mount(MetaBadge, { props: { label: '모델', value: '' } })
    expect(w.find('.meta-badge').exists()).toBe(false)
  })

  it('variant 속성 data-attr 반영', () => {
    const w = mount(MetaBadge, { props: { label: '코호트', value: '균형', variant: 'info' } })
    expect(w.find('.meta-badge').attributes('data-variant')).toBe('info')
  })

  it('tooltip 속성 title 로 반영', () => {
    const w = mount(MetaBadge, {
      props: { label: '모델', value: 'v9', tooltip: '캡스톤 baseline' },
    })
    expect(w.find('.meta-badge').attributes('title')).toBe('캡스톤 baseline')
  })

  it('default variant 적용', () => {
    const w = mount(MetaBadge, { props: { label: '다양성', value: '상관' } })
    expect(w.find('.meta-badge').attributes('data-variant')).toBe('default')
  })
})

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CoverageBadge from '@/components/CoverageBadge.vue'

describe('CoverageBadge', () => {
  it("status='ok' → 렌더링 안 함", () => {
    const w = mount(CoverageBadge, { props: { status: 'ok' } })
    expect(w.find('.coverage-badge').exists()).toBe(false)
  })

  it("status='insufficient_data' → 표시", () => {
    const w = mount(CoverageBadge, { props: { status: 'insufficient_data' } })
    expect(w.find('.coverage-badge').exists()).toBe(true)
    expect(w.text()).toContain('신규 상장')
    expect(w.text()).toContain('분석 충분치 않음')
  })

  it('availableDays + threshold 표시', () => {
    const w = mount(CoverageBadge, {
      props: { status: 'insufficient_data', availableDays: 30, threshold: 60 },
    })
    expect(w.text()).toContain('30일')
    expect(w.text()).toContain('60일')
  })

  it('availableDays 부재 시 일수 small 안 보임', () => {
    const w = mount(CoverageBadge, { props: { status: 'insufficient_data' } })
    expect(w.find('small').exists()).toBe(false)
  })

  it('status=null → 렌더링 안 함 (graceful)', () => {
    const w = mount(CoverageBadge, { props: { status: null } })
    expect(w.find('.coverage-badge').exists()).toBe(false)
  })

  it('status=undefined → 렌더링 안 함', () => {
    const w = mount(CoverageBadge, { props: { status: undefined } })
    expect(w.find('.coverage-badge').exists()).toBe(false)
  })

  it('알 수 없는 status → 렌더링 안 함 (보수적)', () => {
    const w = mount(CoverageBadge, { props: { status: 'unknown_status' } })
    expect(w.find('.coverage-badge').exists()).toBe(false)
  })

  it('role=status 접근성', () => {
    const w = mount(CoverageBadge, { props: { status: 'insufficient_data' } })
    expect(w.find('[role="status"]').exists()).toBe(true)
  })
})

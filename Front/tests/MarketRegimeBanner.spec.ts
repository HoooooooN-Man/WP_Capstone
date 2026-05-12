import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MarketRegimeBanner from '@/components/MarketRegimeBanner.vue'

describe('MarketRegimeBanner', () => {
  it("regime='normal' → 렌더링 안 함", () => {
    const w = mount(MarketRegimeBanner, { props: { regime: 'normal' } })
    expect(w.find('.regime-banner').exists()).toBe(false)
  })

  it("regime='extreme_volatility' → 배너 표시", () => {
    const w = mount(MarketRegimeBanner, { props: { regime: 'extreme_volatility' } })
    expect(w.find('.regime-banner').exists()).toBe(true)
    expect(w.text()).toContain('시장 변동성 경고')
  })

  it('자문 면책 문구 포함', () => {
    const w = mount(MarketRegimeBanner, { props: { regime: 'extreme_volatility' } })
    expect(w.text()).toContain('자문이 아닙니다')
  })

  it('role=alert 접근성', () => {
    const w = mount(MarketRegimeBanner, { props: { regime: 'extreme_volatility' } })
    expect(w.find('[role="alert"]').exists()).toBe(true)
  })

  it('regime=null → 렌더링 안 함 (graceful)', () => {
    const w = mount(MarketRegimeBanner, { props: { regime: null } })
    expect(w.find('.regime-banner').exists()).toBe(false)
  })

  it('regime=undefined → 렌더링 안 함', () => {
    const w = mount(MarketRegimeBanner, { props: { regime: undefined } })
    expect(w.find('.regime-banner').exists()).toBe(false)
  })

  it('알 수 없는 regime → 렌더링 안 함 (보수적)', () => {
    const w = mount(MarketRegimeBanner, { props: { regime: 'future_unknown' } })
    expect(w.find('.regime-banner').exists()).toBe(false)
  })
})

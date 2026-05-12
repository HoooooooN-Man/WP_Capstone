import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NotificationDropdown from '@/components/NotificationDropdown.vue'

describe('NotificationDropdown', () => {
  it('빈 list → "새 알림이 없습니다"', () => {
    const w = mount(NotificationDropdown, { props: { list: [] } })
    expect(w.text()).toContain('새 알림이 없습니다')
    expect(w.find('.notification-dropdown__list').exists()).toBe(false)
  })

  it('list 항목 렌더 (title)', () => {
    const w = mount(NotificationDropdown, {
      props: { list: [{ id: 1, title: '점수 변화' }] },
    })
    expect(w.text()).toContain('점수 변화')
    expect(w.find('.notification-dropdown__empty').exists()).toBe(false)
  })

  it('message fallback (title 없을 때)', () => {
    const w = mount(NotificationDropdown, {
      props: { list: [{ id: 1, message: 'fallback msg' }] },
    })
    expect(w.text()).toContain('fallback msg')
  })

  it('body 있으면 보조 텍스트로 표시', () => {
    const w = mount(NotificationDropdown, {
      props: { list: [{ id: 1, title: 'T', body: '본문 내용' }] },
    })
    expect(w.text()).toContain('본문 내용')
    expect(w.find('.notification-dropdown__body').exists()).toBe(true)
  })

  it('body 없으면 보조 텍스트 미표시', () => {
    const w = mount(NotificationDropdown, {
      props: { list: [{ id: 1, title: 'T' }] },
    })
    expect(w.find('.notification-dropdown__body').exists()).toBe(false)
  })

  it('여러 항목 렌더', () => {
    const list = [1, 2, 3].map(i => ({ id: i, title: `알림 ${i}` }))
    const w = mount(NotificationDropdown, { props: { list } })
    expect(w.findAll('.notification-dropdown__item')).toHaveLength(3)
  })

  it('헤더 "알림" 고정 표시', () => {
    const w = mount(NotificationDropdown, { props: { list: [] } })
    expect(w.find('.notification-dropdown__head').text()).toBe('알림')
  })

  it('role=menu 접근성', () => {
    const w = mount(NotificationDropdown, { props: { list: [] } })
    expect(w.find('[role="menu"]').exists()).toBe(true)
    expect(w.find('[aria-label]').attributes('aria-label')).toBe('알림 목록')
  })

  it('id 없는 항목도 graceful (index fallback)', () => {
    const w = mount(NotificationDropdown, {
      props: { list: [{ title: 'no-id' }, { title: 'also no-id' }] },
    })
    expect(w.findAll('.notification-dropdown__item')).toHaveLength(2)
  })
})

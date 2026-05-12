import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import NotificationBell from '@/components/NotificationBell.vue'

// useNotificationStore mock — 실 store (notifications.js) 의존 회피.
// 같은 id 'notifications' 로 정의해 컴포넌트 import 가 mock 을 받게.
function makeFakeNotifStore(unread = 0, list: any[] = []) {
  return defineStore('notifications', () => {
    const _unread = ref(unread)
    const _list   = ref(list)
    const markCalls = ref(0)
    return {
      unread: _unread,
      list:   _list,
      markCalls,
      markAllRead: () => { markCalls.value++; _unread.value = 0 },
    }
  })
}

describe('NotificationBell', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('unread=0 → badge 미표시', () => {
    makeFakeNotifStore(0)()
    const w = mount(NotificationBell, {
      global: { plugins: [createPinia()] },
    })
    // 새 pinia 라 unread 기본값 — store hot reload 회피용 단순 검증.
    expect(w.find('.notification-bell__badge').exists()).toBe(false)
  })

  it('unread > 0 → badge 표시 + 숫자', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const useFake = makeFakeNotifStore(3)
    useFake()
    const w = mount(NotificationBell, { global: { plugins: [pinia] } })
    expect(w.find('.notification-bell__badge').exists()).toBe(true)
    expect(w.find('.notification-bell__badge').text()).toBe('3')
  })

  it('unread > 9 → "9" cap', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    makeFakeNotifStore(42)()
    const w = mount(NotificationBell, { global: { plugins: [pinia] } })
    expect(w.find('.notification-bell__badge').text()).toBe('9')
  })

  it('aria-label — unread 0 / unread > 0 분기', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    makeFakeNotifStore(0)()
    let w = mount(NotificationBell, { global: { plugins: [pinia] } })
    expect(w.find('button').attributes('aria-label')).toBe('알림')

    const pinia2 = createPinia()
    setActivePinia(pinia2)
    makeFakeNotifStore(2)()
    w = mount(NotificationBell, { global: { plugins: [pinia2] } })
    expect(w.find('button').attributes('aria-label')).toBe('알림 2건')
  })

  it('클릭 → 드롭다운 토글', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    makeFakeNotifStore(0, [])()
    const w = mount(NotificationBell, { global: { plugins: [pinia] } })
    expect(w.find('.notification-bell__dropdown').exists()).toBe(false)
    await w.find('button').trigger('click')
    expect(w.find('.notification-bell__dropdown').exists()).toBe(true)
    await w.find('button').trigger('click')
    expect(w.find('.notification-bell__dropdown').exists()).toBe(false)
  })

  it('드롭다운 열 때 markAllRead 호출', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const useFake = makeFakeNotifStore(5, [{ id: 1, title: 'X' }])
    const store = useFake()
    const w = mount(NotificationBell, { global: { plugins: [pinia] } })
    expect((store as any).markCalls).toBe(0)
    await w.find('button').trigger('click')
    expect((store as any).markCalls).toBe(1)
    expect((store as any).unread).toBe(0)
  })

  it('aria-expanded 동기', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    makeFakeNotifStore(0)()
    const w = mount(NotificationBell, { global: { plugins: [pinia] } })
    expect(w.find('button').attributes('aria-expanded')).toBe('false')
    await w.find('button').trigger('click')
    expect(w.find('button').attributes('aria-expanded')).toBe('true')
  })
})

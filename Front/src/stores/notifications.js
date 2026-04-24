import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/axios.js'

export const useNotificationStore = defineStore('notifications', () => {
  const unread    = ref(0)
  const list      = ref([])
  const permitted = ref(Notification.permission)
  let   timer     = null

  // ── 권한 요청 ────────────────────────────────────────────────────────────────
  async function requestPermission() {
    if (!('Notification' in window)) return
    const result = await Notification.requestPermission()
    permitted.value = result
  }

  // ── 브라우저 알림 발송 ────────────────────────────────────────────────────────
  function push(title, body, url) {
    if (permitted.value !== 'granted') return
    const n = new Notification(title, { body, icon: '/favicon.ico' })
    if (url) n.onclick = () => window.open(url, '_blank')
  }

  // ── 서버 폴링 ────────────────────────────────────────────────────────────────
  async function poll() {
    try {
      const { data } = await api.get('/users/notifications', { params: { unread: true, limit: 10 } })
      const items = data.items ?? data ?? []
      const prevUnread = unread.value
      unread.value = data.unread_count ?? items.length

      // 새 알림이 있으면 브라우저 알림 발송
      if (unread.value > prevUnread && prevUnread >= 0) {
        const newItems = items.slice(0, unread.value - prevUnread)
        newItems.forEach(item => {
          push(
            item.title ?? '새 알림',
            item.body ?? item.message ?? '',
            item.url
          )
        })
      }
      list.value = items
    } catch {
      // 조용히 실패
    }
  }

  // ── 폴링 시작/중단 ───────────────────────────────────────────────────────────
  function startPolling(intervalMs = 5 * 60 * 1000) {
    poll()
    timer = setInterval(poll, intervalMs)
  }

  function stopPolling() {
    if (timer) { clearInterval(timer); timer = null }
  }

  async function markAllRead() {
    try { await api.post('/users/notifications/read-all') } catch {}
    unread.value = 0
    list.value   = list.value.map(n => ({ ...n, is_read: true }))
  }

  return { unread, list, permitted, requestPermission, push, poll, startPolling, stopPolling, markAllRead }
})

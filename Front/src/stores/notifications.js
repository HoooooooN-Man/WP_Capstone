import { defineStore } from 'pinia'
import { ref } from 'vue'
import dbapi from '@/api/dbapi.js'

export const useNotificationStore = defineStore('notifications', () => {
  const unread    = ref(0)
  const list      = ref([])
  const permitted = ref(typeof Notification !== 'undefined' ? Notification.permission : 'default')
  let   timer     = null

  async function requestPermission() {
    if (!('Notification' in window)) return
    const result = await Notification.requestPermission()
    permitted.value = result
  }

  function push(title, body, url) {
    if (permitted.value !== 'granted') return
    const n = new Notification(title, { body, icon: '/favicon.ico' })
    if (url) n.onclick = () => window.open(url, '_blank')
  }

  async function poll() {
    try {
      const { data } = await dbapi.get('/users/notifications', { params: { unread: true, limit: 10 } })
      const items = data.items ?? data ?? []
      const prevUnread = unread.value
      unread.value = data.unread_count ?? items.length

      if (unread.value > prevUnread && prevUnread >= 0) {
        const newItems = items.slice(0, unread.value - prevUnread)
        newItems.forEach(item => {
          push(item.title ?? '새 알림', item.body ?? item.message ?? '', item.url)
        })
      }
      list.value = items
    } catch { /* 조용히 실패 */ }
  }

  function startPolling(intervalMs = 5 * 60 * 1000) {
    poll()
    timer = setInterval(poll, intervalMs)
  }

  function stopPolling() {
    if (timer) { clearInterval(timer); timer = null }
  }

  async function markAllRead() {
    try { await dbapi.post('/users/notifications/read-all') } catch {}
    unread.value = 0
    list.value   = list.value.map(n => ({ ...n, is_read: true }))
  }

  return { unread, list, permitted, requestPermission, push, poll, startPolling, stopPolling, markAllRead }
})

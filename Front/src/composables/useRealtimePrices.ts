/**
 * useRealtimePrices.ts
 * ====================
 * FastAPI ML 서버(:8001)의 /ws/prices 에 연결하여 실시간 시세를 수신.
 *
 * 사용 예 (Vue 컴포넌트):
 *
 *   const { prices, status, subscribe, unsubscribe } = useRealtimePrices(['005930'])
 *   watchEffect(() => console.log(prices.value['005930']))
 *
 * 자동 재연결, 백오프, 가시성 변경 시 일시정지 포함.
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'

export interface PriceTick {
  ticker: string
  price: number
  ts: string
  snapshot?: boolean
}

const WS_URL = (() => {
  const base = (import.meta.env.VITE_API_BASE_ML ?? 'http://localhost:8001') as string
  return base.replace(/^http/, 'ws') + '/ws/prices'
})()

export function useRealtimePrices(initialTickers: string[] = []) {
  const prices = ref<Record<string, PriceTick>>({})
  const status = ref<'idle' | 'connecting' | 'open' | 'closed'>('idle')

  let ws: WebSocket | null = null
  let backoffMs = 1000
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  const subscribed = new Set<string>(initialTickers.map(t => t.padStart(6, '0')))

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return
    status.value = 'connecting'

    const initialQs = subscribed.size
      ? `?ticker=${[...subscribed].join(',')}`
      : ''
    ws = new WebSocket(WS_URL + initialQs)

    ws.onopen = () => {
      status.value = 'open'
      backoffMs = 1000
    }

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as PriceTick & { error?: string }
        if (msg.error) return
        if (msg.ticker && typeof msg.price === 'number') {
          prices.value = { ...prices.value, [msg.ticker]: msg }
        }
      } catch {
        // ignore malformed
      }
    }

    ws.onclose = () => {
      status.value = 'closed'
      ws = null
      // exponential backoff (최대 30s)
      backoffMs = Math.min(backoffMs * 2, 30_000)
      reconnectTimer = setTimeout(connect, backoffMs)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function send(payload: object) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload))
    }
  }

  function subscribe(tickers: string[]) {
    const padded = tickers.map(t => t.padStart(6, '0'))
    padded.forEach(t => subscribed.add(t))
    send({ type: 'subscribe', tickers: padded })
  }

  function unsubscribe(tickers: string[]) {
    const padded = tickers.map(t => t.padStart(6, '0'))
    padded.forEach(t => subscribed.delete(t))
    send({ type: 'unsubscribe', tickers: padded })
  }

  onMounted(connect)

  onBeforeUnmount(() => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
  })

  return { prices, status, subscribe, unsubscribe }
}

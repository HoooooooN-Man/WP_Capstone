/**
 * useRealtimePrices.ts
 * ====================
 * FastAPI ML 서버(:8001)의 /ws/prices 에 연결하여 실시간 시세를 수신.
 *
 * 사용 예 (Vue 컴포넌트):
 *
 *   const { prices, status, isSimulation } = useRealtimePrices(['005930'])
 *   // isSimulation.value === true → "시뮬레이션" 배지 노출
 *
 * 자동 재연결, 백오프, 가시성 변경 시 일시정지 포함.
 *
 * Tier 1.7 (PRD §1.1): 페이로드의 `source` 필드로 시뮬레이션 여부를 판별.
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

export type PriceSource = 'simulation' | 'live'

export interface PriceTick {
  ticker: string
  price: number
  ts: string
  source?: PriceSource    // 백엔드 PRICE_PROVIDER 값. 없으면 보수적으로 simulation 가정.
  delay_ms?: number
  snapshot?: boolean
}

const WS_URL = (() => {
  const base = (import.meta.env.VITE_API_BASE_ML ?? 'http://localhost:8001') as string
  return base.replace(/^http/, 'ws') + '/ws/prices'
})()

export function useRealtimePrices(initialTickers: string[] = []) {
  const prices = ref<Record<string, PriceTick>>({})
  const status = ref<'idle' | 'connecting' | 'open' | 'closed'>('idle')

  // 가장 최근 수신한 페이로드의 source. 한 번이라도 'live' 가 오면 그 이후로 live 로 본다
  // (서로 다른 ticker 가 다른 source 일 수 있는 어댑터에 대비해 보수적으로 마지막 값을 유지).
  const lastSource = ref<PriceSource | undefined>(undefined)
  // 페이로드에 source 필드가 없거나 'simulation' 이면 true. 화면 배지의 신호.
  const isSimulation = computed(() => lastSource.value !== 'live')

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
          if (msg.source === 'simulation' || msg.source === 'live') {
            lastSource.value = msg.source
          }
        }
      } catch (e) {
        // 침묵 실패 금지 (Tier 1.7) — 콘솔에 남김.
        console.error('[useRealtimePrices] malformed message', e)
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

  return { prices, status, isSimulation, lastSource, subscribe, unsubscribe }
}

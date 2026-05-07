import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// ML 분석 서버 (FastAPI :8001) 전용 클라이언트.
// 인증/커뮤니티 서버는 dbapi.js / auth.js 를 사용한다.
const BASE = import.meta.env.VITE_API_BASE_ML ?? 'http://localhost:8001'
const instance = axios.create({
  baseURL: `${BASE}/api/v1`,
  timeout: 30000,
})

// Request interceptor: session token + cohort (W2 자동 첨부)
instance.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers['session-token'] = auth.token
  }

  // W2 — recommendations 요청에 cohort 자동 첨부. 사용자 명시 시 그 값 우선.
  try {
    const url = config.url ?? ''
    if (url.includes('/stocks/recommendations')) {
      const params = config.params ?? {}
      if (!('cohort' in params) || params.cohort == null) {
        const sid = localStorage.getItem('cohort_v1')
        if (sid) {
          config.params = { ...params, cohort: sid }
        }
      }
    }
  } catch {
    /* localStorage 미가용 — 무시 */
  }
  return config
})

// W1D — 추천 응답에 meta.impression_id 가 있으면 :8000 events/impressions 자동 적재.
// fire-and-forget. 적재 실패해도 추천 응답은 정상 전달.
async function _autoLogImpression(res) {
  const meta = res?.data?.meta
  if (!meta || !meta.impression_id) return

  // shown_tickers 추출 — 응답 모양이 라우터마다 다름. items 또는 data.items.
  const list = res?.data?.items || res?.data?.data?.items
  if (!Array.isArray(list) || list.length === 0) return

  const shown = list.slice(0, 100).map((it, i) => ({
    ticker: it.ticker,
    rank: typeof it.rank_in_date === 'number' ? it.rank_in_date : i + 1,
    score: typeof it.score === 'number' ? it.score : undefined,
    tier: typeof it.tier === 'string' ? it.tier : undefined,
  }))

  // page_context 추정 — URL 패턴 기반. 라우터별 정밀화는 W1F 정리에서.
  const url = res.config?.url ?? ''
  const page_context = url.includes('recommendation') ? 'home_recommendations' : 'unknown'

  // 동적 import — 순환 의존성 회피 (events.ts 가 dbapi.js 를 import).
  try {
    const { recordImpressions } = await import('@/api/events')
    await recordImpressions([{
      shown_tickers: shown,
      model_version: meta.model_version ?? 'unknown',
      cohort: meta.cohort ?? null,
      embedding_version: meta.embedding_version ?? null,
      page_context,
    }])
  } catch (e) {
    // events.ts 가 이미 console.error 처리. 추가 noise 방지.
  }
}

// Response interceptor: handle 401 + auto-log impression
instance.interceptors.response.use(
  (res) => {
    // setImmediate-style — 응답 반환은 즉시, 적재는 백그라운드.
    _autoLogImpression(res).catch(() => { /* swallow */ })
    return res
  },
  (err) => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
    }
    return Promise.reject(err)
  }
)

export default instance

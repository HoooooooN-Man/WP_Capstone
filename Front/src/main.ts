import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
// @ts-ignore
import VueVirtualScroller from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

// UX 사이클 W1 — PrimeVue 통합 (Aura preset 시드, 토큰 결정 후 커스텀 preset 교체).
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router/index.js'
import '@/styles/design-tokens.css'   // UX 사이클 W1 — 디자인 토큰 (값은 사용자 결정 후 채움)
import '@/style.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,          // 1분 (기본)
      gcTime: 5 * 60 * 1000,         // 5분 캐시 유지
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(VueQueryPlugin, { queryClient })
app.use(VueVirtualScroller)

// PrimeVue — Aura preset (W1 시드). cssLayer 활성화로 Tailwind v4 우선순위 충돌 회피.
// 토큰 결정 후 themes/<custom>-preset.ts 로 교체 (themes/README.md 참조).
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',
      darkModeSelector: '.dark',
      cssLayer: { name: 'primevue', order: 'tailwind-base, primevue, tailwind-utilities' },
    },
  },
})

// pinia 등록 후 스토어 초기화
// @ts-ignore
import { useAuthStore } from '@/stores/auth.js'
// @ts-ignore
import { useMarketStore } from '@/stores/market.js'
// @ts-ignore
import { useWatchlistStore } from '@/stores/watchlist.js'

const authStore   = useAuthStore()
const marketStore = useMarketStore()
const watchlist   = useWatchlistStore()

authStore.initFromStorage()
watchlist.fetchWatchlist()
marketStore.initVersionsAndDates()

app.use(router)
app.mount('#app')

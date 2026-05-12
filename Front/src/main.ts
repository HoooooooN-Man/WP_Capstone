import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
// @ts-ignore
import VueVirtualScroller from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

// UX 사이클 W1 — PrimeVue 통합. WpPreset (Aura 기반 커스텀, 초안 적용 후 본인 검토 단계).
import PrimeVue from 'primevue/config'
import { WpPreset } from '@/styles/themes/wp-preset'
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

// PrimeVue — WpPreset (Aura 기반 커스텀, Claude 초안). cssLayer 로 Tailwind v4 정합.
app.use(PrimeVue, {
  theme: {
    preset: WpPreset,
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

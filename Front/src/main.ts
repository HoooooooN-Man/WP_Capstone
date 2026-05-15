import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
// @ts-ignore
import VueVirtualScroller from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import App from './App.vue'
import router from './router/index.js'
import '@/style.css'

// Kakao SDK 초기화 - SDK 로드 완료 후 실행
const kakaoKey = import.meta.env.VITE_KAKAO_JS_KEY
if (kakaoKey) {
  if ((window as any).Kakao && !(window as any).Kakao.isInitialized()) {
    (window as any).Kakao.init(kakaoKey)
  }
} else {
  console.warn('VITE_KAKAO_JS_KEY가 설정되지 않았습니다.')
}

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


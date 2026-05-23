import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
// @ts-ignore
import { useAuthStore } from '@/stores/auth.js'
// @ts-ignore
import { useMarketStore } from '@/stores/market.js'
// @ts-ignore
import { useWatchlistStore } from '@/stores/watchlist.js'
// @ts-ignore
import { useThemeStore } from '@/stores/theme.js'
import App from './App.vue'
import '@/style.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      gcTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

const app   = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(VueQueryPlugin, { queryClient })

// pinia 등록 후 스토어 초기화
const authStore   = useAuthStore()
const marketStore = useMarketStore()
const watchlist   = useWatchlistStore()
useThemeStore() // 즉시 다크모드 적용

authStore.initFromStorage()
watchlist.fetchWatchlist()
marketStore.initVersionsAndDates()

app.mount('#app')

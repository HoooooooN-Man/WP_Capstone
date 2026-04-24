import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index.js'
import '@/style.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

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

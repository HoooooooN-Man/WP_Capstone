import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useWatchlistStore = defineStore('watchlist', () => {
  const tickers = ref([])

  const isFavorite = computed(() => (ticker) => tickers.value.includes(ticker))

  function fetchWatchlist() {
    // 로컬 스토리지에서 복원 (추후 API 연동 가능)
    const stored = localStorage.getItem('watchlist')
    if (stored) {
      try { tickers.value = JSON.parse(stored) } catch {}
    }
  }

  function _persist() {
    localStorage.setItem('watchlist', JSON.stringify(tickers.value))
  }

  function addTicker(ticker) {
    if (tickers.value.includes(ticker)) return
    tickers.value.push(ticker)
    _persist()
  }

  function removeTicker(ticker) {
    tickers.value = tickers.value.filter(t => t !== ticker)
    _persist()
  }

  function toggleTicker(ticker) {
    if (tickers.value.includes(ticker)) removeTicker(ticker)
    else addTicker(ticker)
  }

  return { tickers, isFavorite, fetchWatchlist, addTicker, removeTicker, toggleTicker }
})

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { stocksApi } from '@/api/stocks'

const DEFAULT_FILTERS = {
  model_version: 'latest',
  date:          '',
  sector:        '',
  min_score:     0,
  top_k:         50,
}

export const useStocksStore = defineStore('stocks', () => {
  const items      = ref([])
  const totalCount = ref(0)
  const loading    = ref(false)
  const error      = ref(null)
  const filters    = ref({ ...DEFAULT_FILTERS })

  const tierCounts = computed(() => {
    const counts = { A: 0, B: 0, C: 0, D: 0 }
    items.value.forEach(i => { if (i.tier in counts) counts[i.tier]++ })
    return counts
  })

  async function fetchRecommendations() {
    loading.value = true
    error.value   = null
    try {
      const params = {}
      if (filters.value.model_version) params.model_version = filters.value.model_version
      if (filters.value.date)          params.date          = filters.value.date
      if (filters.value.sector)        params.sector        = filters.value.sector
      if (filters.value.min_score > 0) params.min_score     = filters.value.min_score
      if (filters.value.top_k > 0)     params.top_k         = filters.value.top_k

      const res    = await stocksApi.getRecommendations(params)
      items.value  = res.data.items ?? []
      totalCount.value = res.data.total ?? 0
    } catch (e) {
      error.value = e?.response?.data?.detail ?? '데이터를 불러오지 못했습니다.'
    } finally {
      loading.value = false
    }
  }

  function setFilter(key, value) {
    filters.value[key] = value
  }

  function resetFilters() {
    filters.value = { ...DEFAULT_FILTERS }
  }

  return { items, totalCount, loading, error, filters, tierCounts, fetchRecommendations, setFilter, resetFilters }
})

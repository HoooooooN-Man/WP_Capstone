import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { stocksApi } from '@/api/stocks'

export const useStocksStore = defineStore('stocks', () => {
  const items      = ref([])
  const totalCount = ref(0)
  const loading    = ref(false)
  const error      = ref(null)
  const versions   = ref([])
  const dates      = ref([])
  const filters    = ref({
    model_version: 'latest',
    date:          null,
    sector:        null,
    min_score:     0,
    top_k:         0,
  })

  const tierCounts = computed(() => {
    const c = { A: 0, B: 0, C: 0, D: 0 }
    items.value.forEach(i => { if (c[i.tier] !== undefined) c[i.tier]++ })
    return c
  })

  async function initVersionsAndDates() {
    try {
      const { data: v } = await stocksApi.getVersions()
      versions.value = v.versions ?? []
      filters.value.model_version = v.latest ?? 'latest'

      const { data: d } = await stocksApi.getDates(v.latest)
      dates.value = d.dates ?? []
      filters.value.date = d.latest ?? null
    } catch (e) {
      console.error('[stocksStore] initVersionsAndDates failed', e)
    }
  }

  async function fetchRecommendations() {
    loading.value = true
    error.value   = null
    try {
      const params = { ...filters.value }
      if (!params.sector)    delete params.sector
      if (!params.date)      delete params.date
      if (!params.min_score) delete params.min_score

      const { data } = await stocksApi.getRecommendations(params)
      items.value      = data.items  ?? []
      totalCount.value = data.total  ?? 0
    } catch (e) {
      error.value = e.response?.status === 404 ? 'no_data' : 'error'
      items.value = []
    } finally {
      loading.value = false
    }
  }

  function setFilter(key, value) {
    filters.value[key] = value
  }

  function resetFilters() {
    filters.value.sector    = null
    filters.value.min_score = 0
    filters.value.top_k     = 0
  }

  return {
    items, totalCount, loading, error, versions, dates, filters,
    tierCounts, initVersionsAndDates, fetchRecommendations, setFilter, resetFilters,
  }
})

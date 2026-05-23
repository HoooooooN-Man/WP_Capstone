import { defineStore } from 'pinia'
import { ref } from 'vue'
import { stocksApi } from '@/api/stocks.js'

export const useMarketStore = defineStore('market', () => {
  const selectedVersion = ref('latest')
  const selectedDate    = ref('')
  const versions        = ref([])
  const dates           = ref([])
  const sectorSummary   = ref([])
  const topStocks       = ref([])
  const loading         = ref(false)

  async function initVersionsAndDates() {
    try {
      const vRes = await stocksApi.getVersions()
      versions.value = vRes.data.versions ?? []
      selectedVersion.value = vRes.data.latest ?? 'latest'

      const dRes = await stocksApi.getDates('latest')
      dates.value = dRes.data.dates ?? []
      selectedDate.value = dRes.data.latest ?? ''
    } catch (e) {
      console.error('[marketStore] initVersionsAndDates failed', e)
    }
  }

  async function fetchSectorSummary() {
    loading.value = true
    try {
      const { data } = await stocksApi.getSectorsSummary({
        model_version: selectedVersion.value,
        date: selectedDate.value || undefined,
      })
      sectorSummary.value = data.items ?? []
    } catch {
      sectorSummary.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchTopStocks(limit = 5) {
    try {
      const { data } = await stocksApi.getRecommendations({
        model_version: selectedVersion.value,
        date: selectedDate.value || undefined,
        top_k: limit,
      })
      topStocks.value = data.items ?? []
    } catch {
      topStocks.value = []
    }
  }

  async function setVersion(v) {
    selectedVersion.value = v
    try {
      const dRes = await stocksApi.getDates(v)
      dates.value = dRes.data.dates ?? []
      selectedDate.value = dRes.data.latest ?? ''
    } catch (e) {
      console.error('[marketStore] setVersion failed', e)
    }
  }

  function setDate(d) {
    selectedDate.value = d
  }

  return {
    selectedVersion, selectedDate, versions, dates,
    sectorSummary, topStocks, loading,
    initVersionsAndDates, fetchSectorSummary, fetchTopStocks, setVersion, setDate,
  }
})

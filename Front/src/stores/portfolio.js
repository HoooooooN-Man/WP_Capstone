import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { portfolioApi } from '@/api/portfolio'
import { stocksApi } from '@/api/stocks'

export const usePortfolioStore = defineStore('portfolio', () => {
  const growthItems    = ref([])
  const stableItems    = ref([])
  const growthDate     = ref(null)
  const stableDate     = ref(null)
  const backtestSummary  = ref(null)
  const backtestMonthly  = ref([])
  const loading          = ref(false)
  const backtestLoading  = ref(false)
  const activeType       = ref('growth')
  const selectedVersion  = ref('latest')
  const versions         = ref([])
  const growthLoaded     = ref(false)
  const stableLoaded     = ref(false)

  async function initVersions() {
    const { data } = await stocksApi.getVersions()
    versions.value = data.versions ?? []
    selectedVersion.value = data.latest ?? 'latest'
  }

  async function fetchPortfolio(type) {
    if (type === 'growth' && growthLoaded.value) return
    if (type === 'stable' && stableLoaded.value) return

    loading.value = true
    try {
      const { data } = await portfolioApi.getKospi200(type, selectedVersion.value)
      if (type === 'growth') {
        growthItems.value  = data.items ?? []
        growthDate.value   = data.date  ?? null
        growthLoaded.value = true
      } else {
        stableItems.value  = data.items ?? []
        stableDate.value   = data.date  ?? null
        stableLoaded.value = true
      }
    } catch (e) {
      if (type === 'growth') { growthItems.value = []; growthLoaded.value = false }
      else                   { stableItems.value = []; stableLoaded.value = false }
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchBacktest() {
    backtestLoading.value = true
    try {
      const [s, m] = await Promise.all([
        portfolioApi.getBacktestSummary(),
        portfolioApi.getBacktestMonthly(),
      ])
      backtestSummary.value = s.data
      backtestMonthly.value = m.data.data ?? []
    } catch {}
    finally {
      backtestLoading.value = false
    }
  }

  function setType(type) {
    activeType.value = type
  }

  async function changeVersion(ver) {
    selectedVersion.value = ver
    growthLoaded.value    = false
    stableLoaded.value    = false
    await fetchPortfolio(activeType.value)
  }

  const currentItems = computed(() =>
    activeType.value === 'growth' ? growthItems.value : stableItems.value
  )
  const currentDate = computed(() =>
    activeType.value === 'growth' ? growthDate.value : stableDate.value
  )

  return {
    growthItems, stableItems, growthDate, stableDate,
    backtestSummary, backtestMonthly,
    loading, backtestLoading,
    activeType, selectedVersion, versions,
    currentItems, currentDate,
    initVersions, fetchPortfolio, fetchBacktest, setType, changeVersion,
  }
})

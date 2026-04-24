import { defineStore } from 'pinia'
import { ref } from 'vue'
import { portfolioApi } from '@/api/portfolio'

export const usePortfolioStore = defineStore('portfolio', () => {
  const growthItems      = ref([])
  const stableItems      = ref([])
  const backtestSummary  = ref(null)
  const backtestMonthly  = ref([])
  const loading          = ref(false)
  const activeType       = ref('growth')
  const selectedVersion  = ref('latest')
  const growthLoaded     = ref(false)
  const stableLoaded     = ref(false)

  async function fetchPortfolio(type) {
    if (type === 'growth' && growthLoaded.value) return
    if (type === 'stable' && stableLoaded.value) return

    loading.value = true
    try {
      const res = await portfolioApi.getKospi200(type, selectedVersion.value)
      if (type === 'growth') {
        growthItems.value  = res.data.items ?? []
        growthLoaded.value = true
      } else {
        stableItems.value  = res.data.items ?? []
        stableLoaded.value = true
      }
    } catch (e) {
      console.error(`[portfolioStore] fetchPortfolio(${type}) failed`, e)
    } finally {
      loading.value = false
    }
  }

  async function fetchBacktest() {
    try {
      const [sumRes, monRes] = await Promise.all([
        portfolioApi.getBacktestSummary(),
        portfolioApi.getBacktestMonthly(),
      ])
      backtestSummary.value = sumRes.data ?? null
      backtestMonthly.value = monRes.data?.data ?? []
    } catch (e) {
      console.error('[portfolioStore] fetchBacktest failed', e)
    }
  }

  async function setType(type) {
    activeType.value = type
    await fetchPortfolio(type)
  }

  return {
    growthItems, stableItems, backtestSummary, backtestMonthly,
    loading, activeType, selectedVersion, growthLoaded, stableLoaded,
    fetchPortfolio, fetchBacktest, setType,
  }
})

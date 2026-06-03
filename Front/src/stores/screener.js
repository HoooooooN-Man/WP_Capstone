import { defineStore } from 'pinia'
import { ref } from 'vue'
import { stocksApi } from '@/api/stocks.js'

const TIER_MIN_SCORE = { A: 80, B: 60, C: 40, D: 0 }

export const useScreenerStore = defineStore('screener', () => {
  const items   = ref([])
  const total   = ref(0)
  const loading = ref(false)
  const error   = ref(null)

  const filters = ref({
    model_version:     'latest',
    min_score:         0,
    tier:              null,
    sector:            null,
    max_per:           null,
    max_pbr:           null,
    min_roe:           null,
    max_debt_ratio:    null,
    min_op_margin:     null,
    min_rev_growth:    null,
    min_finance_score: null,
    sort_by:           'composite_score',
    limit:             50,
  })

  async function fetchScreener() {
    loading.value = true
    error.value   = null
    try {
      const f = filters.value
      const params = {}
      if (f.model_version) params.model_version = f.model_version
      if (f.sector)        params.sector        = f.sector
      if (f.tier)          params.tier          = f.tier
      // tier → min_score 변환
      const tierMin  = f.tier ? (TIER_MIN_SCORE[f.tier] ?? 0) : 0
      const minScore = Math.max(Number(f.min_score ?? 0), tierMin)
      if (minScore > 0) params.min_score = minScore
      if (f.max_per)           params.max_per           = f.max_per
      if (f.max_pbr)           params.max_pbr           = f.max_pbr
      if (f.min_roe)           params.min_roe           = f.min_roe
      if (f.max_debt_ratio)    params.max_debt_ratio    = f.max_debt_ratio
      if (f.min_op_margin)     params.min_op_margin     = f.min_op_margin
      if (f.min_rev_growth)    params.min_rev_growth    = f.min_rev_growth
      if (f.min_finance_score) params.min_finance_score = f.min_finance_score
      params.sort_by = f.sort_by ?? 'composite_score'
      params.limit   = f.limit   ?? 50
      const { data } = await stocksApi.getScreener(params)
      items.value = data.items ?? []
      total.value = data.total ?? 0
    } catch (e) {
      error.value = 'error'
      items.value = []
    } finally {
      loading.value = false
    }
  }

  function setFilter(key, value) {
    filters.value[key] = value === '' ? null : value
  }

  function resetAllFilters() {
    filters.value.max_per           = null
    filters.value.max_pbr           = null
    filters.value.min_roe           = null
    filters.value.max_debt_ratio    = null
    filters.value.min_op_margin     = null
    filters.value.min_rev_growth    = null
    filters.value.min_finance_score = null
    filters.value.min_score         = 0
    filters.value.tier              = null
    filters.value.sector            = null
  }

  return { items, total, loading, error, filters, fetchScreener, setFilter, resetAllFilters }
})

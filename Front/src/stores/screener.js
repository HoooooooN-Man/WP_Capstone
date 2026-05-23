import { defineStore } from 'pinia'
import { ref } from 'vue'
import { screenerApi } from '@/api/screener.js'

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
      const params = Object.fromEntries(
        Object.entries(filters.value).filter(([k, v]) => v !== null && v !== '' && v !== undefined && (v !== 0 || k === 'min_score'))
      )
      if (params.min_score === 0) delete params.min_score
      const { data } = await screenerApi.getScreener(params)
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

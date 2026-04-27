import { defineStore } from 'pinia'
import { ref } from 'vue'
import { screenerApi } from '@/api/screener'

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
        Object.entries(filters.value).filter(([_, v]) => v !== null && v !== '' && v !== undefined && v !== 0 || v === 0 && _ === 'min_score')
      )
      // min_score=0 은 불필요하므로 제거
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

  function resetFinancialFilters() {
    filters.value.max_per           = null
    filters.value.max_pbr           = null
    filters.value.min_roe           = null
    filters.value.max_debt_ratio    = null
    filters.value.min_op_margin     = null
    filters.value.min_rev_growth    = null
    filters.value.min_finance_score = null
  }

  function resetAllFilters() {
    resetFinancialFilters()
    filters.value.min_score = 0
    filters.value.tier      = null
    filters.value.sector    = null
  }

  function savePreset(name) {
    const presets = JSON.parse(localStorage.getItem('screener_presets') || '{}')
    presets[name] = { ...filters.value }
    localStorage.setItem('screener_presets', JSON.stringify(presets))
  }

  function loadPreset(name) {
    const presets = JSON.parse(localStorage.getItem('screener_presets') || '{}')
    if (presets[name]) filters.value = { ...filters.value, ...presets[name] }
  }

  function deletePreset(name) {
    const presets = JSON.parse(localStorage.getItem('screener_presets') || '{}')
    delete presets[name]
    localStorage.setItem('screener_presets', JSON.stringify(presets))
  }

  function getSavedPresets() {
    return Object.keys(JSON.parse(localStorage.getItem('screener_presets') || '{}'))
  }

  return {
    items, total, loading, error, filters,
    fetchScreener, setFilter, resetFinancialFilters, resetAllFilters,
    savePreset, loadPreset, deletePreset, getSavedPresets,
  }
})

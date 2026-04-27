import { defineStore } from 'pinia'
import { ref } from 'vue'
import { stocksApi } from '@/api/stocks'

export const useMarketStore = defineStore('market', () => {
  const selectedVersion = ref('latest')
  const selectedDate    = ref('')
  const versions        = ref([])
  const dates           = ref([])

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

  return { selectedVersion, selectedDate, versions, dates, initVersionsAndDates, setVersion, setDate }
})

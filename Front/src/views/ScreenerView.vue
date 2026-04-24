<script setup>
import { onMounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { useScreenerStore } from '@/stores/screener'
import FilterSidebar from '@/components/screener/FilterSidebar.vue'
import ScreenerTable from '@/components/screener/ScreenerTable.vue'

const store = useScreenerStore()

const fetchDebounced = useDebounceFn(() => store.fetchScreener(), 500)

function onFilterChange({ key, value }) {
  if (key === '_reload') { store.fetchScreener(); return }
  store.setFilter(key, value)
  fetchDebounced()
}

function onResetFinancial() {
  store.resetFinancialFilters()
  store.fetchScreener()
}

function onResetAll() {
  store.resetAllFilters()
  store.fetchScreener()
}

onMounted(async () => {
  await store.fetchScreener()
})
</script>

<template>
  <div class="max-w-[1400px] mx-auto px-4 py-6">

    <!-- 페이지 제목 -->
    <div class="mb-5">
      <h1 class="text-xl font-semibold text-gray-900">스크리너</h1>
      <p class="text-sm text-gray-400 mt-1">ML 점수와 재무 지표를 조합해 종목을 필터링합니다</p>
    </div>

    <!-- 2컬럼 레이아웃 -->
    <div class="grid grid-cols-[300px_1fr] gap-6 items-start">

      <FilterSidebar
        :filters="store.filters"
        @filter-change="onFilterChange"
        @reset-financial="onResetFinancial"
        @reset-all="onResetAll"
      />

      <ScreenerTable
        :items="store.items"
        :total="store.total"
        :loading="store.loading"
        :error="store.error"
        @reset-financial="onResetFinancial"
      />

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { useStocksStore } from '@/stores/stocks'
import FilterPanel  from '@/components/stocks/FilterPanel.vue'
import StockTable   from '@/components/stocks/StockTable.vue'
import SummaryPanel from '@/components/stocks/SummaryPanel.vue'
import ProbDrawer   from '@/components/stocks/ProbDrawer.vue'

const route  = useRoute()
const router = useRouter()
const store  = useStocksStore()

// 드로어 상태
const drawerOpen  = ref(false)
const drawerStock = ref(null)

function openDrawer(stock) {
  drawerStock.value = stock
  drawerOpen.value  = true
}

// 필터 변경
const fetchDebounced = useDebounceFn(() => store.fetchRecommendations(), 300)

function handleFilterChange({ key, value }) {
  store.setFilter(key, value)
  if (key === 'date' || key === 'model_version') {
    store.fetchRecommendations()
  } else {
    fetchDebounced()
  }
}

function handleReset() {
  store.resetFilters()
  store.fetchRecommendations()
}

// CSV 내보내기
function exportCsv() {
  const header = 'rank,ticker,name,sector,score,tier'
  const rows   = store.items.map((item, i) =>
    [i + 1, item.ticker, item.name, item.sector, item.score, item.tier].join(',')
  )
  const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
  const a    = document.createElement('a')
  a.href     = URL.createObjectURL(blob)
  a.download = `stocks_${store.filters.date ?? 'latest'}.csv`
  a.click()
}

// 초기화
onMounted(async () => {
  if (!store.versions.length) await store.initVersionsAndDates()

  // 라우터 쿼리 섹터 반영
  if (route.query.sector) {
    store.setFilter('sector', route.query.sector)
  }
  await store.fetchRecommendations()
})
</script>

<template>
  <div class="max-w-[1400px] mx-auto px-4 py-6">

    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-5">
      <div class="flex items-center gap-3">
        <h1 class="text-xl font-semibold text-gray-900">종목 추천</h1>
        <span class="bg-gray-100 text-gray-500 text-xs rounded-full px-2.5 py-1">
          {{ store.totalCount.toLocaleString() }}종목
        </span>
      </div>
      <button
        class="text-sm text-gray-500 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors"
        @click="exportCsv"
      >
        CSV 내보내기
      </button>
    </div>

    <!-- 3컬럼 레이아웃 -->
    <div class="grid grid-cols-[260px_1fr_280px] gap-6 items-start">

      <!-- 필터 패널 -->
      <FilterPanel
        :versions="store.versions"
        :dates="store.dates"
        :filters="store.filters"
        @filter-change="handleFilterChange"
        @reset="handleReset"
      />

      <!-- 종목 테이블 -->
      <StockTable
        :items="store.items"
        :loading="store.loading"
        :error="store.error"
        @row-click="openDrawer"
      />

      <!-- 요약 패널 -->
      <SummaryPanel
        :tier-counts="store.tierCounts"
        :items="store.items"
      />

    </div>

  </div>

  <!-- 확률 드로어 -->
  <ProbDrawer
    :stock="drawerStock"
    :open="drawerOpen"
    @close="drawerOpen = false"
  />
</template>

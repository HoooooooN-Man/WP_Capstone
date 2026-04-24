<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme.js'
import { useDebounceFn } from '@vueuse/core'
import { useStocksStore } from '@/stores/stocks'
import FilterPanel  from '@/components/stocks/FilterPanel.vue'
import StockTable   from '@/components/stocks/StockTable.vue'
import SummaryPanel from '@/components/stocks/SummaryPanel.vue'
import ProbDrawer   from '@/components/stocks/ProbDrawer.vue'

const route  = useRoute()
const router = useRouter()
const store  = useStocksStore()
const theme  = useThemeStore()

// 모바일 필터 시트
const filterSheetOpen = ref(false)

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
  <div class="max-w-[1400px] mx-auto px-4 py-4 md:py-6 pb-20 md:pb-6">

    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-4 md:mb-5">
      <div class="flex items-center gap-3">
        <h1 class="text-lg md:text-xl font-semibold">종목 추천</h1>
        <span
          class="text-xs rounded-full px-2.5 py-1"
          :class="theme.isDark ? 'bg-white/10 text-gray-400' : 'bg-gray-100 text-gray-500'"
        >
          {{ store.totalCount.toLocaleString() }}종목
        </span>
      </div>
      <div class="flex items-center gap-2">
        <!-- 모바일: 필터 버튼 -->
        <button
          class="md:hidden text-sm border rounded-lg px-3 py-1.5 transition-colors"
          :class="theme.isDark ? 'border-[#2A2D3A] text-gray-400 hover:bg-white/10' : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
          @click="filterSheetOpen = true"
        >
          🔧 필터
        </button>
        <button
          class="text-sm border rounded-lg px-3 py-1.5 transition-colors"
          :class="theme.isDark ? 'border-[#2A2D3A] text-gray-400 hover:bg-white/10' : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
          @click="exportCsv"
        >
          CSV
        </button>
      </div>
    </div>

    <!-- 데스크톱: 3컬럼 레이아웃 -->
    <div class="hidden md:grid grid-cols-[260px_1fr_280px] gap-6 items-start">
      <FilterPanel
        :versions="store.versions"
        :dates="store.dates"
        :filters="store.filters"
        @filter-change="handleFilterChange"
        @reset="handleReset"
      />
      <StockTable
        :items="store.items"
        :loading="store.loading"
        :error="store.error"
        @row-click="openDrawer"
      />
      <SummaryPanel
        :tier-counts="store.tierCounts"
        :items="store.items"
      />
    </div>

    <!-- 모바일: 단일 컬럼 -->
    <div class="md:hidden">
      <StockTable
        :items="store.items"
        :loading="store.loading"
        :error="store.error"
        @row-click="openDrawer"
      />
    </div>

  </div>

  <!-- 확률 드로어 -->
  <ProbDrawer
    :stock="drawerStock"
    :open="drawerOpen"
    @close="drawerOpen = false"
  />

  <!-- 모바일 필터 Bottom Sheet -->
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="filterSheetOpen" class="fixed inset-0 z-[70] md:hidden">
        <div class="absolute inset-0 bg-black/50" @click="filterSheetOpen = false" />
        <div
          class="absolute bottom-0 left-0 right-0 rounded-t-2xl max-h-[85vh] overflow-y-auto"
          :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-white'"
        >
          <!-- 핸들 -->
          <div class="flex justify-center pt-3 pb-2">
            <div class="w-10 h-1 rounded-full bg-gray-300" />
          </div>
          <div class="flex items-center justify-between px-5 pb-3">
            <h3 class="font-semibold">필터</h3>
            <button @click="filterSheetOpen = false">✕</button>
          </div>
          <div class="px-4 pb-8">
            <FilterPanel
              :versions="store.versions"
              :dates="store.dates"
              :filters="store.filters"
              @filter-change="(e) => { handleFilterChange(e); }"
              @reset="handleReset"
            />
          </div>
          <div class="px-4 pb-6">
            <button
              class="w-full py-3 rounded-xl font-medium text-sm transition-colors"
              :class="theme.isDark ? 'bg-white/10 text-white' : 'bg-gray-900 text-white'"
              @click="filterSheetOpen = false"
            >
              적용하기
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-enter-active, .sheet-leave-active { transition: opacity 0.25s; }
.sheet-enter-from, .sheet-leave-to { opacity: 0; }
.sheet-enter-active > div:last-child,
.sheet-leave-active > div:last-child { transition: transform 0.25s ease; }
.sheet-enter-from > div:last-child,
.sheet-leave-to > div:last-child { transform: translateY(100%); }
</style>

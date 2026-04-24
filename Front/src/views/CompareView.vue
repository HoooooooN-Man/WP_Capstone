<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { stocksApi } from '@/api/stocks'
import StockSearchSelector from '@/components/compare/StockSearchSelector.vue'
import ScoreHistoryChart   from '@/components/compare/ScoreHistoryChart.vue'
import StockSummaryCards   from '@/components/compare/StockSummaryCards.vue'
import FinanceCompareTable from '@/components/compare/FinanceCompareTable.vue'

const route  = useRoute()
const router = useRouter()

const STOCK_COLORS = [
  '#7F77DD', '#1D9E75', '#378ADD', '#D85A30',
  '#BA7517', '#D4537E', '#639922', '#888780', '#E24B4A', '#0F6E56',
]

// ── 상태 ──────────────────────────────────────────────────────────────────────
const selectedTickers = ref([])          // string[]
const stockNames      = ref({})          // ticker → name
const compareResults  = ref([])          // API items
const colorMap        = ref({})          // ticker → color
const hiddenTickers   = reactive(new Set())
const selectedPeriod  = ref('1y')
const loading         = ref(false)
const error           = ref(null)

const PERIODS = [
  { label: '3개월', value: '3m' },
  { label: '6개월', value: '6m' },
  { label: '1년',   value: '1y' },
  { label: '3년',   value: '3y' },
  { label: '전체',  value: 'all' },
]

const canCompare = computed(() => selectedTickers.value.length >= 2)

// ── URL 동기화 ─────────────────────────────────────────────────────────────────
function syncUrl() {
  router.replace({
    query: {
      ...(selectedTickers.value.length > 0 && { tickers: selectedTickers.value.join(',') }),
      ...(selectedPeriod.value !== '1y' && { period: selectedPeriod.value }),
    },
  })
}

// ── API ───────────────────────────────────────────────────────────────────────
async function fetchCompare() {
  if (!canCompare.value) return
  loading.value = true
  error.value   = null
  try {
    const { data } = await stocksApi.getCompare(
      selectedTickers.value.join(','),
      'latest',
      selectedPeriod.value
    )
    compareResults.value = data.items ?? []
    // 이름 캐시 업데이트
    compareResults.value.forEach(r => { stockNames.value[r.ticker] = r.name })
  } catch (e) {
    error.value = 'error'
  } finally {
    loading.value = false
  }
}

// ── 종목 추가/삭제 ────────────────────────────────────────────────────────────
function addTicker(item) {
  if (!selectedTickers.value.includes(item.ticker)) {
    const colorIdx = selectedTickers.value.length % STOCK_COLORS.length
    colorMap.value[item.ticker] = STOCK_COLORS[colorIdx]
    stockNames.value[item.ticker] = item.name
    selectedTickers.value.push(item.ticker)
    syncUrl()
  }
}

function removeTicker(ticker) {
  selectedTickers.value = selectedTickers.value.filter(t => t !== ticker)
  delete colorMap.value[ticker]
  compareResults.value = compareResults.value.filter(r => r.ticker !== ticker)
  hiddenTickers.delete(ticker)
  syncUrl()
}

function toggleHidden(ticker) {
  if (hiddenTickers.has(ticker)) hiddenTickers.delete(ticker)
  else hiddenTickers.add(ticker)
}

// ── 기간 변경 ─────────────────────────────────────────────────────────────────
async function onPeriodChange(period) {
  selectedPeriod.value = period
  syncUrl()
  if (canCompare.value) await fetchCompare()
}

// ── 초기 로드 ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  if (route.query.period) selectedPeriod.value = route.query.period

  if (route.query.tickers) {
    const tickers = route.query.tickers.split(',').filter(Boolean)
    tickers.forEach((t, i) => {
      colorMap.value[t] = STOCK_COLORS[i % STOCK_COLORS.length]
      selectedTickers.value.push(t)
    })
    if (tickers.length >= 2) await fetchCompare()
  }
})
</script>

<template>
  <div class="max-w-5xl mx-auto px-6 py-8 flex flex-col gap-6">

    <div>
      <h1 class="text-xl font-semibold text-gray-900 mb-1">종목 비교</h1>
      <p class="text-sm text-gray-400">최대 10개 종목을 선택해 ML 점수와 재무 지표를 비교합니다</p>
    </div>

    <!-- 종목 검색 선택기 -->
    <StockSearchSelector
      :selected-tickers="selectedTickers"
      :color-map="colorMap"
      :stock-names="stockNames"
      @add-ticker="addTicker"
      @remove-ticker="removeTicker"
    />

    <!-- 비교 버튼 -->
    <div class="flex items-center gap-3">
      <button
        class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        :class="canCompare
          ? 'bg-blue-600 text-white hover:bg-blue-700'
          : 'bg-gray-100 text-gray-300 cursor-not-allowed'"
        :disabled="!canCompare"
        @click="fetchCompare"
      >
        비교하기
      </button>
      <span v-if="!canCompare" class="text-xs text-gray-400">종목을 2개 이상 선택해주세요</span>
    </div>

    <!-- 기간 탭 -->
    <div class="flex gap-1">
      <button
        v-for="p in PERIODS"
        :key="p.value"
        class="px-3 py-1.5 text-xs rounded-lg border transition-colors"
        :class="selectedPeriod === p.value
          ? 'bg-gray-900 text-white border-gray-900'
          : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
        @click="onPeriodChange(p.value)"
      >
        {{ p.label }}
      </button>
    </div>

    <!-- 빈 상태 (2개 미만) -->
    <div v-if="!canCompare" class="flex flex-col items-center py-16 gap-3">
      <!-- 두 원이 겹치는 아이콘 -->
      <svg width="64" height="48" viewBox="0 0 64 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="22" cy="24" r="18" fill="#e5e7eb" />
        <circle cx="42" cy="24" r="18" fill="#d1d5db" />
      </svg>
      <p class="text-gray-500">2개 이상의 종목을 선택해 주세요</p>
      <p class="text-sm text-gray-400">위 검색창에서 종목을 추가하세요</p>
    </div>

    <!-- 로딩 -->
    <div v-else-if="loading" class="flex flex-col gap-4">
      <div v-for="h in [280, 120, 200]" :key="h" class="bg-gray-100 rounded-xl animate-pulse" :style="{ height: h + 'px' }" />
    </div>

    <!-- 에러 -->
    <div v-else-if="error" class="text-center text-gray-500 py-8">
      데이터를 불러오지 못했습니다
    </div>

    <!-- 비교 결과 -->
    <template v-else-if="compareResults.length">
      <ScoreHistoryChart
        :results="compareResults"
        :color-map="colorMap"
        :hidden-tickers="hiddenTickers"
        @toggle-ticker="toggleHidden"
      />

      <StockSummaryCards
        :results="compareResults"
        :color-map="colorMap"
      />

      <FinanceCompareTable
        :results="compareResults"
        :color-map="colorMap"
      />
    </template>

  </div>
</template>

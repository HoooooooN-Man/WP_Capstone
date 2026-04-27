<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { chartApi }   from '@/api/chart'
import { financeApi } from '@/api/finance'
import { stocksApi }  from '@/api/stocks'
import { useAuthStore }      from '@/stores/auth.js'
import { useWatchlistStore } from '@/stores/watchlist.js'

import StockHeader       from '@/components/stockDetail/StockHeader.vue'
import CandleChart       from '@/components/stockDetail/CandleChart.vue'
import VolumeChart       from '@/components/stockDetail/VolumeChart.vue'
import ScoreHistoryChart from '@/components/stockDetail/ScoreHistoryChart.vue'
import FinanceSummary    from '@/components/stockDetail/FinanceSummary.vue'
import FinanceTable      from '@/components/stockDetail/FinanceTable.vue'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()
const watchlist = useWatchlistStore()

const ticker = route.params.ticker

// ── 상태 ──────────────────────────────────────────────────────────────────────
const candles        = ref([])
const financeLatest  = ref(null)
const financeHistory = ref([])
const scoreHistory   = ref([])

const loading     = ref(true)
const notFound    = ref(false)
const activePeriod = ref('1y')
const activeTab   = ref('summary')
const showLoginModal = ref(false)

const PERIODS = [
  { label: '1개월', value: '1m' },
  { label: '3개월', value: '3m' },
  { label: '6개월', value: '6m' },
  { label: '1년',   value: '1y' },
  { label: '3년',   value: '3y' },
  { label: '전체',  value: 'all' },
]

// ── 파생 데이터 ────────────────────────────────────────────────────────────────
const stockInfo = computed(() => {
  if (candles.value.length) return { name: chartName.value, sector: '', midSector: '' }
  return {}
})
const chartName     = ref('')
const chartSector   = ref('')

const latestScore = computed(() => scoreHistory.value.at(-1)?.score   ?? 0)
const latestTier  = computed(() => scoreHistory.value.at(-1)?.tier    ?? 'D')
const latestScoreItem = computed(() => scoreHistory.value.at(-1) ?? null)

const isFavorite = computed(() => watchlist.isFavorite(ticker))

// ── API 함수들 ─────────────────────────────────────────────────────────────────
async function fetchChart(period) {
  try {
    const res = await chartApi.getCandles(ticker, period)
    candles.value   = res.data.items ?? []
    chartName.value = res.data.name  ?? ticker
  } catch (e) {
    if (e?.response?.status === 404) notFound.value = true
  }
}

async function fetchFinanceLatest() {
  try {
    const res = await financeApi.getLatest(ticker)
    financeLatest.value = res.data
  } catch {}
}

async function fetchFinanceHistory() {
  try {
    const res = await financeApi.getHistory(ticker, 20)
    financeHistory.value = res.data.items ?? []
  } catch {}
}

async function fetchScoreHistory() {
  try {
    const res = await stocksApi.getHistory(ticker, { model_version: 'latest' })
    scoreHistory.value = res.data.items ?? []
  } catch {}
}

async function changePeriod(p) {
  activePeriod.value = p
  await fetchChart(p)
}

// ── 관심종목 토글 ──────────────────────────────────────────────────────────────
function toggleFavorite() {
  if (!auth.isLoggedIn) { showLoginModal.value = true; return }
  watchlist.toggleTicker(ticker)
}

// ── 초기 로드 ──────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    fetchChart('1y'),
    fetchFinanceLatest(),
    fetchFinanceHistory(),
    fetchScoreHistory(),
  ])
  loading.value = false
})
</script>

<template>
  <!-- 전체 페이지 스켈레톤 -->
  <div v-if="loading" class="max-w-5xl mx-auto px-6 py-6 flex flex-col gap-4">
    <div v-for="h in [80, 320, 80, 160, 200]" :key="h"
      class="bg-gray-100 rounded-xl animate-pulse"
      :style="{ height: h + 'px' }"
    />
  </div>

  <!-- 404 -->
  <div v-else-if="notFound" class="flex items-center justify-center min-h-[60vh]">
    <div class="text-center space-y-3">
      <p class="text-gray-700 font-medium">종목 정보를 찾을 수 없습니다</p>
      <button
        class="text-sm text-gray-500 border border-gray-200 rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors"
        @click="router.back()"
      >
        ← 목록으로 돌아가기
      </button>
    </div>
  </div>

  <!-- 정상 페이지 -->
  <div v-else class="max-w-5xl mx-auto px-6 py-6 flex flex-col gap-4">

    <!-- 헤더 -->
    <StockHeader
      :ticker="ticker"
      :name="chartName"
      :sector="chartSector"
      :latest-score="latestScore"
      :latest-tier="latestTier"
      :is-favorite="isFavorite"
      @toggle-favorite="toggleFavorite"
    />

    <!-- 기간 탭 -->
    <div class="flex gap-1">
      <button
        v-for="p in PERIODS"
        :key="p.value"
        class="px-3 py-1.5 text-xs rounded-lg border transition-colors"
        :class="activePeriod === p.value
          ? 'bg-gray-900 text-white border-gray-900'
          : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
        @click="changePeriod(p.value)"
      >
        {{ p.label }}
      </button>
    </div>

    <!-- 캔들 차트 -->
    <CandleChart :candles="candles" :ticker="ticker" />

    <!-- 거래량 차트 -->
    <VolumeChart :candles="candles" />

    <!-- ML 점수 이력 -->
    <ScoreHistoryChart :history="scoreHistory" />

    <!-- 재무 탭 -->
    <div>
      <!-- 탭 버튼 -->
      <div class="flex gap-1 mb-3">
        <button
          v-for="tab in [{ value: 'summary', label: '재무 요약' }, { value: 'table', label: '분기별 재무' }]"
          :key="tab.value"
          class="px-3 py-1.5 text-sm rounded-lg border transition-colors"
          :class="activeTab === tab.value
            ? 'bg-gray-900 text-white border-gray-900'
            : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>

      <FinanceSummary
        v-if="activeTab === 'summary'"
        :latest="financeLatest"
        :score-item="latestScoreItem"
      />
      <FinanceTable
        v-else
        :items="financeHistory"
      />
    </div>

  </div>

  <!-- 로그인 모달 -->
  <Transition name="fade">
    <div
      v-if="showLoginModal"
      class="fixed inset-0 bg-black/30 z-50 flex items-center justify-center"
      @click.self="showLoginModal = false"
    >
      <div class="bg-white rounded-xl p-6 max-w-sm w-full mx-4 flex flex-col gap-4">
        <p class="text-center text-gray-800">관심종목 추가는 로그인이 필요합니다</p>
        <div class="flex gap-2">
          <button
            class="flex-1 bg-gray-900 text-white rounded-lg py-2.5 text-sm hover:bg-gray-700 transition-colors"
            @click="router.push('/login')"
          >
            로그인하기
          </button>
          <button
            class="flex-1 border border-gray-200 text-gray-500 rounded-lg py-2.5 text-sm hover:bg-gray-50 transition-colors"
            @click="showLoginModal = false"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

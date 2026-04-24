<script setup>
import { ref, onMounted } from 'vue'
import { usePortfolioStore } from '@/stores/portfolio.js'
import StrategyTabs          from '@/components/portfolio/StrategyTabs.vue'
import PortfolioCardGrid     from '@/components/portfolio/PortfolioCardGrid.vue'
import StrategyExplanation   from '@/components/portfolio/StrategyExplanation.vue'
import BacktestSummaryTable  from '@/components/portfolio/BacktestSummaryTable.vue'
import BacktestMonthlyChart  from '@/components/portfolio/BacktestMonthlyChart.vue'

const store = usePortfolioStore()

const portfolioError = ref(null)
const backtestOpen   = ref(true)
const rawOpen        = ref(false)

// ── 이벤트 핸들러 ─────────────────────────────────────────────────────────────
async function onTypeChange(type) {
  store.setType(type)
  portfolioError.value = null
  try {
    await store.fetchPortfolio(type)
  } catch (e) {
    portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error'
  }
}

async function onVersionChange(ver) {
  try {
    await store.changeVersion(ver)
  } catch (e) {
    portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error'
  }
}

// ── 초기 로드 ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  await store.initVersions()
  await Promise.all([
    store.fetchPortfolio('growth').catch(e => {
      portfolioError.value = e?.response?.status === 404 ? 'not_ready' : 'error'
    }),
    store.fetchBacktest(),
  ])
})
</script>

<template>
  <div class="max-w-5xl mx-auto px-6 py-8 flex flex-col gap-8">

    <!-- ── Section 1: 포트폴리오 전략 ── -->
    <div class="flex flex-col gap-4">
      <h1 class="text-xl font-semibold text-gray-900">포트폴리오</h1>

      <StrategyTabs
        :active-type="store.activeType"
        :versions="store.versions"
        :selected-version="store.selectedVersion"
        :current-date="store.currentDate"
        @type-change="onTypeChange"
        @version-change="onVersionChange"
      />

      <PortfolioCardGrid
        :items="store.currentItems"
        :type="store.activeType"
        :loading="store.loading"
        :error="portfolioError"
      />

      <StrategyExplanation :type="store.activeType" />
    </div>

    <hr class="border-gray-100" />

    <!-- ── Section 2: 백테스트 ── -->
    <div class="flex flex-col gap-4">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-semibold text-gray-900">백테스트 결과</h2>
        <button
          class="text-xs text-gray-400 hover:text-gray-600 transition-colors border border-gray-200 rounded-lg px-2.5 py-1.5"
          @click="backtestOpen = !backtestOpen"
        >
          {{ backtestOpen ? '▲ 접기' : '▼ 펼치기' }}
        </button>
      </div>

      <template v-if="backtestOpen">

        <!-- 로딩 -->
        <div v-if="store.backtestLoading" class="h-32 bg-gray-100 rounded-xl animate-pulse" />

        <template v-else>
          <BacktestSummaryTable :summary="store.backtestSummary" />
          <BacktestMonthlyChart :data="store.backtestMonthly" />

          <!-- 원문 결과 아코디언 -->
          <div>
            <button
              class="text-sm text-gray-500 hover:text-gray-700 transition-colors"
              @click="rawOpen = !rawOpen"
            >
              {{ rawOpen ? '▲ 원문 결과 닫기' : '▼ 원문 결과 보기' }}
            </button>
            <pre
              v-if="rawOpen"
              class="mt-2 text-xs text-gray-600 bg-gray-50 rounded-xl p-4 overflow-x-auto whitespace-pre-wrap"
            >{{ store.backtestSummary?.v8_walk_forward }}</pre>
          </div>
        </template>

      </template>
    </div>

  </div>
</template>

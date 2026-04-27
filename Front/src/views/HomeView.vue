<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { stocksApi } from '@/api/stocks.js'
import api from '@/api/axios.js'
import MarketRegimeBanner from '@/components/home/MarketRegimeBanner.vue'
import SummaryCards       from '@/components/home/SummaryCards.vue'
import SectorSummaryTable from '@/components/home/SectorSummaryTable.vue'
import TopStocksPreview   from '@/components/home/TopStocksPreview.vue'

const router = useRouter()

// ── 상태 ─────────────────────────────────────────────────────────────────────
const versions        = ref([])
const dates           = ref([])
const selectedVersion = ref('latest')
const selectedDate    = ref('')

const regime          = ref(null)
const sectors         = ref([])
const topStocks       = ref([])

const loading         = ref(false)
const error           = ref(null)

// ── 데이터 로드 ───────────────────────────────────────────────────────────────
async function loadMeta() {
  try {
    const vRes = await stocksApi.getVersions()
    versions.value = vRes.data.versions ?? []
    selectedVersion.value = vRes.data.latest ?? 'latest'

    const dRes = await stocksApi.getDates('latest')
    dates.value = dRes.data.dates ?? []
    selectedDate.value = dRes.data.latest ?? ''
  } catch (e) {
    console.error('loadMeta failed', e)
  }
}

async function loadDashboard() {
  loading.value = true
  error.value   = null
  try {
    const ver  = selectedVersion.value
    const date = selectedDate.value

    const [regRes, secRes, topRes] = await Promise.all([
      api.get('/market/regime', { params: { model_version: ver } }),
      stocksApi.getSectorsSummary({ date, model_version: ver }),
      stocksApi.getRecommendations({ date, model_version: ver, top_k: 5 }),
    ])

    regime.value    = regRes.data
    sectors.value   = secRes.data.items ?? []
    topStocks.value = topRes.data.items ?? []
  } catch (e) {
    if (e?.response?.status === 503) {
      error.value = '서비스 준비 중입니다. ML 데이터를 적재하는 중이에요.'
    } else {
      error.value = '데이터를 불러오지 못했습니다.'
    }
  } finally {
    loading.value = false
  }
}

// ── 라이프사이클 ──────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadMeta()
  await loadDashboard()
})

watch([selectedVersion, selectedDate], () => {
  loadDashboard()
})

// ── 이벤트 ───────────────────────────────────────────────────────────────────
function onSectorClick(sector) {
  router.push({ path: '/stocks', query: { sector } })
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-6 flex flex-col gap-5">

    <!-- 서비스 에러 배너 -->
    <div v-if="error" class="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-700">
      {{ error }}
    </div>

    <!-- ── 마켓 레이더 배너 ── -->
    <template v-if="loading && !regime">
      <div class="h-24 bg-gray-100 rounded-xl animate-pulse" />
    </template>
    <MarketRegimeBanner
      v-else
      :regime="regime"
      :versions="versions"
      :dates="dates"
      :selected-version="selectedVersion"
      :selected-date="selectedDate"
      @update:selected-version="v => { selectedVersion = v }"
      @update:selected-date="d => { selectedDate = d }"
    />

    <!-- ── 요약 카드 ── -->
    <template v-if="loading && !regime">
      <div class="grid grid-cols-3 gap-3">
        <div v-for="i in 3" :key="i" class="h-20 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    </template>
    <SummaryCards v-else :regime="regime" />

    <!-- ── 2컬럼 그리드 ── -->
    <div class="grid grid-cols-5 gap-5">

      <!-- 섹터 요약 테이블 (60%) -->
      <div class="col-span-3 flex flex-col gap-2">
        <h2 class="text-sm font-medium text-gray-700">섹터별 현황</h2>
        <div v-if="loading && !sectors.length" class="h-64 bg-gray-100 rounded-xl animate-pulse" />
        <SectorSummaryTable
          v-else
          :items="sectors"
          @sector-click="onSectorClick"
        />
      </div>

      <!-- 상위 종목 (40%) -->
      <div class="col-span-2 flex flex-col gap-2">
        <h2 class="text-sm font-medium text-gray-700">오늘의 Top 5</h2>
        <div v-if="loading && !topStocks.length" class="flex flex-col gap-2">
          <div v-for="i in 5" :key="i" class="h-14 bg-gray-100 rounded-xl animate-pulse" />
        </div>
        <TopStocksPreview v-else :items="topStocks" />
      </div>

    </div>

  </div>
</template>

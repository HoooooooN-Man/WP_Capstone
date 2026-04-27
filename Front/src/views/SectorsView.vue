<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Chart, registerables } from 'chart.js'
import { TreemapController, TreemapElement } from 'chartjs-chart-treemap'
import { useThemeStore } from '@/stores/theme.js'
import api from '@/api/axios.js'

Chart.register(...registerables, TreemapController, TreemapElement)

const router = useRouter()
const theme  = useThemeStore()

const loading = ref(false)
const error   = ref(null)
const sectors = ref([])
const chartEl = ref(null)
let chartInst = null

// ── 데이터 fetch ──────────────────────────────────────────────────────────────
async function fetchSectors() {
  loading.value = true
  error.value   = null
  try {
    const { data } = await api.get('/stocks/sectors/summary')
    // 응답 형태: [{ sector, count, avg_score, top_tier }]
    sectors.value = (data.sectors ?? data ?? []).filter(s => s.count > 0)
  } catch (e) {
    error.value = e?.response?.data?.detail ?? '데이터를 불러오지 못했습니다.'
    // 모의 데이터 (API 미연결 시)
    sectors.value = mockSectors()
  } finally {
    loading.value = false
    renderChart()
  }
}

function mockSectors() {
  return [
    { sector: 'IT', count: 45, avg_score: 72.4, top_tier: 'A' },
    { sector: '헬스케어', count: 32, avg_score: 68.1, top_tier: 'B' },
    { sector: '금융', count: 28, avg_score: 61.5, top_tier: 'B' },
    { sector: '산업재', count: 25, avg_score: 58.2, top_tier: 'C' },
    { sector: '소재', count: 20, avg_score: 55.8, top_tier: 'C' },
    { sector: '에너지', count: 18, avg_score: 53.1, top_tier: 'C' },
    { sector: '통신', count: 15, avg_score: 64.3, top_tier: 'B' },
    { sector: '유틸리티', count: 12, avg_score: 49.7, top_tier: 'D' },
    { sector: '소비재', count: 22, avg_score: 60.3, top_tier: 'B' },
    { sector: '필수소비재', count: 17, avg_score: 57.6, top_tier: 'C' },
  ]
}

// ── 점수 → 색상 ───────────────────────────────────────────────────────────────
function scoreToColor(score, dark = false) {
  if (score >= 70) return dark ? 'rgba(239,68,68,0.85)' : 'rgba(220,38,38,0.8)'
  if (score >= 60) return dark ? 'rgba(249,115,22,0.8)' : 'rgba(234,88,12,0.75)'
  if (score >= 50) return dark ? 'rgba(234,179,8,0.8)'  : 'rgba(202,138,4,0.75)'
  return dark ? 'rgba(107,114,128,0.75)' : 'rgba(107,114,128,0.65)'
}

// ── Chart.js 트리맵 렌더 ──────────────────────────────────────────────────────
function renderChart() {
  if (!chartEl.value || !sectors.value.length) return
  const dark = theme.isDark

  if (chartInst) { chartInst.destroy(); chartInst = null }

  chartInst = new Chart(chartEl.value, {
    type: 'treemap',
    data: {
      datasets: [{
        label: '섹터',
        tree: sectors.value,
        key: 'count',
        groups: ['sector'],
        backgroundColor(ctx) {
          const raw = ctx.raw?._data
          if (!raw) return dark ? '#2A2D3A' : '#E5E7EB'
          const score = raw.avg_score ?? 50
          return scoreToColor(score, dark)
        },
        borderColor: dark ? '#1A1D27' : '#fff',
        borderWidth: 2,
        labels: {
          display: true,
          align: 'center',
          position: 'middle',
          color: '#fff',
          font: { size: 12, weight: 'bold' },
          formatter(ctx) {
            const d = ctx.raw?._data
            if (!d) return ''
            return [d.sector, `${d.avg_score?.toFixed(1)}점`]
          },
        },
        captions: {
          display: false,
        },
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title(items) { return items[0].raw?._data?.sector ?? '' },
            label(item) {
              const d = item.raw?._data
              if (!d) return ''
              return [
                `종목 수: ${d.count}개`,
                `평균 ML점수: ${d.avg_score?.toFixed(1)}`,
                `대표 등급: ${d.top_tier ?? '-'}`,
              ]
            },
          },
        },
      },
      onClick(_e, elements) {
        if (!elements.length) return
        const d = elements[0].element?.$context?.raw?._data
        if (d?.sector) router.push(`/stocks?sector=${encodeURIComponent(d.sector)}`)
      },
    },
  })
}

// ── 통계 ──────────────────────────────────────────────────────────────────────
const totalCount  = computed(() => sectors.value.reduce((s, r) => s + r.count, 0))
const avgScore    = computed(() => {
  if (!sectors.value.length) return 0
  const ws = sectors.value.reduce((s, r) => s + r.avg_score * r.count, 0)
  return (ws / totalCount.value).toFixed(1)
})
const topSector   = computed(() =>
  [...sectors.value].sort((a, b) => b.avg_score - a.avg_score)[0]?.sector ?? '-'
)

// ── 점수 범위별 색상 범례 ──────────────────────────────────────────────────────
const legend = [
  { label: '70점 이상', color: 'bg-red-500' },
  { label: '60–70점',   color: 'bg-orange-500' },
  { label: '50–60점',   color: 'bg-yellow-500' },
  { label: '50점 미만', color: 'bg-gray-500' },
]

onMounted(fetchSectors)
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 md:py-6 pb-20 md:pb-6">

    <!-- 헤더 -->
    <div class="mb-6">
      <h1 class="text-xl font-semibold">섹터 히트맵</h1>
      <p class="text-sm mt-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
        박스 크기 = 종목 수 &nbsp;·&nbsp; 색상 강도 = 평균 ML점수 &nbsp;·&nbsp; 클릭 시 해당 섹터 종목 이동
      </p>
    </div>

    <!-- 요약 카드 -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div
        class="rounded-xl p-4"
        :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
      >
        <p class="text-xs mb-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">전체 종목 수</p>
        <p class="text-2xl font-bold">{{ totalCount.toLocaleString() }}</p>
      </div>
      <div
        class="rounded-xl p-4"
        :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
      >
        <p class="text-xs mb-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">가중평균 ML점수</p>
        <p class="text-2xl font-bold">{{ avgScore }}<span class="text-base font-normal ml-1">점</span></p>
      </div>
      <div
        class="rounded-xl p-4"
        :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
      >
        <p class="text-xs mb-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">최고 섹터</p>
        <p class="text-2xl font-bold truncate">{{ topSector }}</p>
      </div>
    </div>

    <!-- 트리맵 차트 -->
    <div
      class="rounded-2xl overflow-hidden mb-6"
      :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
    >
      <div v-if="loading" class="flex items-center justify-center h-[420px]">
        <div class="w-8 h-8 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
      </div>
      <div v-else-if="!sectors.length" class="flex items-center justify-center h-[420px]">
        <p class="text-sm" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
          {{ error ?? '데이터가 없습니다' }}
        </p>
      </div>
      <div v-else class="p-4" style="height: 480px; position: relative;">
        <canvas ref="chartEl" />
      </div>
    </div>

    <!-- 색상 범례 -->
    <div class="flex items-center flex-wrap gap-4 mb-6">
      <span class="text-sm" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">색상 기준:</span>
      <div v-for="l in legend" :key="l.label" class="flex items-center gap-1.5">
        <div class="w-3 h-3 rounded-sm" :class="l.color" />
        <span class="text-xs" :class="theme.isDark ? 'text-gray-400' : 'text-gray-600'">{{ l.label }}</span>
      </div>
    </div>

    <!-- 섹터 테이블 -->
    <div
      class="rounded-2xl overflow-hidden"
      :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
    >
      <div class="px-5 py-4 border-b" :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'">
        <h2 class="font-semibold text-sm">섹터별 요약</h2>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr :class="theme.isDark ? 'bg-[#0F1117]' : 'bg-gray-50'">
              <th class="text-left px-5 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">섹터</th>
              <th class="text-right px-5 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">종목 수</th>
              <th class="text-right px-5 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">평균 ML점수</th>
              <th class="px-5 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">점수 분포</th>
              <th class="px-5 py-3 text-xs font-medium" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in [...sectors].sort((a,b) => b.avg_score - a.avg_score)"
              :key="s.sector"
              class="border-t transition-colors cursor-pointer"
              :class="theme.isDark
                ? 'border-[#2A2D3A] hover:bg-white/5'
                : 'border-gray-50 hover:bg-gray-50'"
              @click="router.push(`/stocks?sector=${encodeURIComponent(s.sector)}`)"
            >
              <td class="px-5 py-3 font-medium">{{ s.sector }}</td>
              <td class="px-5 py-3 text-right" :class="theme.isDark ? 'text-gray-400' : 'text-gray-600'">{{ s.count }}</td>
              <td class="px-5 py-3 text-right font-semibold">{{ s.avg_score?.toFixed(1) }}</td>
              <td class="px-5 py-3 w-40">
                <div class="h-1.5 rounded-full overflow-hidden" :class="theme.isDark ? 'bg-[#0F1117]' : 'bg-gray-100'">
                  <div
                    class="h-full rounded-full transition-all"
                    :style="{ width: `${Math.min(100, s.avg_score)}%`, background: scoreToColor(s.avg_score, theme.isDark) }"
                  />
                </div>
              </td>
              <td class="px-5 py-3 text-right">
                <span class="text-xs" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">→</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

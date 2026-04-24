<script setup>
import { ref, computed } from 'vue'
import { useThemeStore } from '@/stores/theme.js'
import api from '@/api/axios.js'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, LineElement, PointElement, LinearScale, CategoryScale, Legend, Tooltip, Filler } from 'chart.js'

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Legend, Tooltip, Filler)

const theme = useThemeStore()

// ── 조건 입력 ──────────────────────────────────────────────────────────────────
const form = ref({
  min_score:   60,
  top_k:       20,
  rebalance:   'monthly',   // 'monthly' | 'quarterly'
  start_date:  '2023-01-01',
  end_date:    '2024-12-31',
  model_version: 'latest',
})

const loading  = ref(false)
const error    = ref(null)
const result   = ref(null)

// ── API 호출 ──────────────────────────────────────────────────────────────────
async function runBacktest() {
  loading.value = true
  error.value   = null
  result.value  = null
  try {
    const { data } = await api.post('/portfolio/backtest', form.value)
    result.value = data
  } catch (e) {
    error.value = e?.response?.data?.detail ?? 'API 연결 실패. 모의 결과를 표시합니다.'
    result.value = mockResult()
  } finally {
    loading.value = false
  }
}

function mockResult() {
  const months = []
  const stratRet = [], benchRet = []
  let strat = 100, bench = 100
  for (let m = 0; m < 24; m++) {
    const d = new Date(2023, m, 1)
    months.push(d.toLocaleDateString('ko-KR', { year: '2-digit', month: 'short' }))
    const sr = (Math.random() * 8 - 2)
    const br = (Math.random() * 5 - 1.5)
    strat += sr; bench += br
    stratRet.push(+strat.toFixed(2))
    benchRet.push(+bench.toFixed(2))
  }
  const finalStrat = stratRet[stratRet.length - 1] - 100
  const finalBench = benchRet[benchRet.length - 1] - 100
  return {
    total_return: finalStrat,
    benchmark_return: finalBench,
    mdd: -(Math.random() * 15 + 5),
    sharpe: +(Math.random() * 1.5 + 0.5).toFixed(2),
    win_rate: +(Math.random() * 20 + 55).toFixed(1),
    trade_count: Math.floor(Math.random() * 200 + 50),
    monthly: months.map((month, i) => ({
      month,
      strategy: stratRet[i],
      benchmark: benchRet[i],
    })),
  }
}

// ── 차트 데이터 ───────────────────────────────────────────────────────────────
const chartData = computed(() => {
  if (!result.value?.monthly) return null
  const labels = result.value.monthly.map(m => m.month)
  const strat  = result.value.monthly.map(m => m.strategy)
  const bench  = result.value.monthly.map(m => m.benchmark)

  return {
    labels,
    datasets: [
      {
        label: '전략 수익률',
        data: strat,
        borderColor: '#5B6DFF',
        backgroundColor: 'rgba(91,109,255,0.08)',
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 2,
      },
      {
        label: 'KOSPI 벤치마크',
        data: bench,
        borderColor: theme.isDark ? '#6B7280' : '#D1D5DB',
        borderWidth: 1.5,
        borderDash: [4, 4],
        tension: 0.3,
        fill: false,
        pointRadius: 0,
      },
    ],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { color: theme.isDark ? '#9BA4B5' : '#6B7280', font: { size: 12 } },
    },
    tooltip: { mode: 'index', intersect: false },
  },
  scales: {
    x: {
      grid: { color: theme.isDark ? '#2A2D3A' : '#F3F4F6' },
      ticks: { color: theme.isDark ? '#6B7280' : '#9CA3AF', font: { size: 11 } },
    },
    y: {
      grid: { color: theme.isDark ? '#2A2D3A' : '#F3F4F6' },
      ticks: {
        color: theme.isDark ? '#6B7280' : '#9CA3AF',
        font: { size: 11 },
        callback: (v) => v.toFixed(0) + '%',
      },
    },
  },
}))

const summaryCards = computed(() => {
  if (!result.value) return []
  const r = result.value
  return [
    { label: '전략 누적 수익률', value: `${r.total_return >= 0 ? '+' : ''}${r.total_return?.toFixed(2)}%`,
      color: r.total_return >= 0 ? 'text-red-500' : 'text-blue-500' },
    { label: 'KOSPI 대비',       value: `${(r.total_return - r.benchmark_return) >= 0 ? '+' : ''}${(r.total_return - r.benchmark_return).toFixed(2)}%`,
      color: (r.total_return - r.benchmark_return) >= 0 ? 'text-red-500' : 'text-blue-500' },
    { label: '최대 낙폭 (MDD)',   value: `${r.mdd?.toFixed(2)}%`, color: 'text-orange-500' },
    { label: '샤프 지수',         value: r.sharpe?.toFixed(2), color: 'text-indigo-500' },
    { label: '승률',              value: `${r.win_rate?.toFixed(1)}%`, color: '' },
    { label: '거래 횟수',         value: `${r.trade_count}회`, color: '' },
  ]
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-4 md:py-6 pb-20 md:pb-6">

    <!-- 헤더 -->
    <div class="mb-6">
      <h1 class="text-xl font-semibold">백테스트 시뮬레이터</h1>
      <p class="text-sm mt-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
        투자 전략 조건을 설정하고 과거 수익률을 시뮬레이션합니다
      </p>
    </div>

    <!-- 조건 설정 카드 -->
    <div
      class="rounded-2xl p-5 mb-6 border"
      :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
    >
      <h2 class="font-semibold text-sm mb-4">전략 조건</h2>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div>
          <label class="text-xs mb-1.5 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
            최소 ML 점수 ({{ form.min_score }})
          </label>
          <input
            v-model.number="form.min_score"
            type="range" min="0" max="100" step="5"
            class="w-full accent-indigo-500"
          />
          <div class="flex justify-between text-xs mt-0.5" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">
            <span>0</span><span>100</span>
          </div>
        </div>
        <div>
          <label class="text-xs mb-1.5 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">최대 보유 종목 수</label>
          <input
            v-model.number="form.top_k"
            type="number" min="5" max="100"
            class="w-full rounded-lg px-3 py-2 text-sm border outline-none"
            :class="theme.isDark ? 'bg-[#0F1117] border-[#2A2D3A] text-white' : 'bg-gray-50 border-gray-200'"
          />
        </div>
        <div>
          <label class="text-xs mb-1.5 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">리밸런싱 주기</label>
          <select
            v-model="form.rebalance"
            class="w-full rounded-lg px-3 py-2 text-sm border outline-none"
            :class="theme.isDark ? 'bg-[#0F1117] border-[#2A2D3A] text-white' : 'bg-gray-50 border-gray-200'"
          >
            <option value="monthly">매월</option>
            <option value="quarterly">분기</option>
          </select>
        </div>
        <div>
          <label class="text-xs mb-1.5 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">시작일</label>
          <input
            v-model="form.start_date"
            type="date"
            class="w-full rounded-lg px-3 py-2 text-sm border outline-none"
            :class="theme.isDark ? 'bg-[#0F1117] border-[#2A2D3A] text-white' : 'bg-gray-50 border-gray-200'"
          />
        </div>
        <div>
          <label class="text-xs mb-1.5 block" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">종료일</label>
          <input
            v-model="form.end_date"
            type="date"
            class="w-full rounded-lg px-3 py-2 text-sm border outline-none"
            :class="theme.isDark ? 'bg-[#0F1117] border-[#2A2D3A] text-white' : 'bg-gray-50 border-gray-200'"
          />
        </div>
        <div class="flex items-end">
          <button
            class="w-full py-2.5 rounded-lg text-sm font-medium transition-colors"
            :class="loading
              ? (theme.isDark ? 'bg-white/5 text-gray-600' : 'bg-gray-100 text-gray-400')
              : (theme.isDark ? 'bg-indigo-600 text-white hover:bg-indigo-500' : 'bg-indigo-600 text-white hover:bg-indigo-700')"
            :disabled="loading"
            @click="runBacktest"
          >
            {{ loading ? '계산 중...' : '▶ 시뮬레이션 실행' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 에러 메시지 -->
    <div
      v-if="error"
      class="rounded-xl px-4 py-3 mb-4 text-sm"
      :class="theme.isDark ? 'bg-orange-900/20 text-orange-400' : 'bg-orange-50 text-orange-700'"
    >
      ⚠️ {{ error }}
    </div>

    <!-- 결과 -->
    <div v-if="result">

      <!-- 요약 카드 -->
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
        <div
          v-for="card in summaryCards"
          :key="card.label"
          class="rounded-xl p-4 border"
          :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
        >
          <p class="text-xs mb-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">{{ card.label }}</p>
          <p class="text-xl font-bold" :class="card.color">{{ card.value }}</p>
        </div>
      </div>

      <!-- 누적 수익률 차트 -->
      <div
        class="rounded-2xl p-5 border mb-4"
        :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
      >
        <h2 class="font-semibold text-sm mb-4">누적 수익률 추이</h2>
        <div style="height: 280px">
          <Line v-if="chartData" :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <!-- 조건 요약 -->
      <div
        class="rounded-xl px-4 py-3 text-xs"
        :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A] text-gray-500' : 'bg-gray-50 text-gray-400'"
      >
        조건: ML 점수 {{ form.min_score }}점 이상 · Top {{ form.top_k }}종목 ·
        {{ form.rebalance === 'monthly' ? '월별' : '분기별' }} 리밸런싱 ·
        {{ form.start_date }} ~ {{ form.end_date }}
      </div>

    </div>

    <!-- 초기 안내 -->
    <div
      v-else-if="!loading"
      class="text-center py-16 rounded-2xl"
      :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-gray-50'"
    >
      <p class="text-3xl mb-3">📊</p>
      <p class="text-sm font-medium mb-1">조건을 설정하고 시뮬레이션을 실행하세요</p>
      <p class="text-xs" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
        ML 점수 기반 전략의 과거 수익률을 확인할 수 있습니다
      </p>
    </div>

  </div>
</template>

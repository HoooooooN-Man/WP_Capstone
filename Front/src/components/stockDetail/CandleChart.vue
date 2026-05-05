<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  Chart as ChartJS,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  TimeScale,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import {
  CandlestickController,
  CandlestickElement,
} from 'chartjs-chart-financial'

// chartjs-chart-financial ESM 은 부수효과로 등록하지 않음 — 명시 등록 필요
ChartJS.register(
  CategoryScale,
  LinearScale,
  TimeScale,
  LineElement,
  PointElement,
  BarController,
  BarElement,
  CandlestickController,
  CandlestickElement,
  Tooltip,
  Legend,
)

const props = defineProps({
  candles:    { type: Array, default: () => [] },
  ticker:     { type: String, default: '' },
})

const visibleMAs = ref(new Set(['MA5', 'MA20']))
const canvasRef  = ref(null)
let chart        = null

const MA_COLORS = {
  MA5: '#7F77DD', MA20: '#EF9F27', MA60: '#1D9E75', MA120: '#E24B4A',
}
const MA_KEYS = {
  MA5: 'ma5', MA20: 'ma20', MA60: 'ma60', MA120: 'ma120',
}

function buildDatasets() {
  const ohlc = props.candles.map(c => ({
    x: new Date(c.date).getTime(),
    o: c.open, h: c.high, l: c.low, c: c.close,
  }))

  const datasets = [{
    type: 'candlestick',
    label: props.ticker,
    data: ohlc,
    color: { up: '#1D9E75', down: '#E24B4A', unchanged: '#888780' },
  }]

  for (const [maLabel, maKey] of Object.entries(MA_KEYS)) {
    datasets.push({
      type: 'line',
      label: maLabel,
      data: props.candles.map(c => ({ x: new Date(c.date).getTime(), y: c[maKey] })),
      borderColor: MA_COLORS[maLabel],
      borderWidth: 1,
      pointRadius: 0,
      hidden: !visibleMAs.value.has(maLabel),
    })
  }
  return datasets
}

function buildChart() {
  if (!canvasRef.value || !props.candles.length) return
  if (chart) { chart.destroy(); chart = null }

  chart = new ChartJS(canvasRef.value, {
    type: 'candlestick',
    data: { datasets: buildDatasets() },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: { mode: 'index', intersect: false },
      },
      scales: {
        x: { type: 'time', time: { unit: 'month' }, grid: { display: false } },
        y: { grid: { color: '#f3f4f6' } },
      },
    },
  })
}

function toggleMA(ma) {
  if (visibleMAs.value.has(ma)) visibleMAs.value.delete(ma)
  else visibleMAs.value.add(ma)

  // 차트 데이터셋 hidden 토글
  if (chart) {
    const ds = chart.data.datasets.find(d => d.label === ma)
    if (ds) ds.hidden = !visibleMAs.value.has(ma)
    chart.update()
  }
}

watch(() => props.candles, buildChart, { deep: false })
onMounted(buildChart)
onUnmounted(() => { if (chart) chart.destroy() })
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-100 p-4">
    <!-- MA 토글 버튼 -->
    <div class="flex items-center gap-2 mb-3">
      <span class="text-xs text-gray-400 mr-1">이동평균</span>
      <button
        v-for="ma in ['MA5', 'MA20', 'MA60', 'MA120']"
        :key="ma"
        class="px-2 py-0.5 text-xs rounded-full border transition-colors"
        :style="visibleMAs.has(ma)
          ? { background: MA_COLORS[ma] + '22', borderColor: MA_COLORS[ma], color: MA_COLORS[ma] }
          : { borderColor: '#e5e7eb', color: '#9ca3af' }"
        @click="toggleMA(ma)"
      >
        {{ ma }}
      </button>
    </div>
    <div class="h-[320px]">
      <canvas ref="canvasRef" />
    </div>
  </div>
</template>

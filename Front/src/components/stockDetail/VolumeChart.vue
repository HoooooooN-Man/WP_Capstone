<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, TimeScale, Tooltip } from 'chart.js'
import 'chartjs-adapter-date-fns'

ChartJS.register(BarElement, CategoryScale, LinearScale, TimeScale, Tooltip)

const props  = defineProps({ candles: { type: Array, default: () => [] } })
const canvasRef = ref(null)
let chart = null

function buildChart() {
  if (!canvasRef.value || !props.candles.length) return
  if (chart) { chart.destroy(); chart = null }

  chart = new ChartJS(canvasRef.value, {
    type: 'bar',
    data: {
      datasets: [{
        label: '거래량',
        data: props.candles.map(c => ({ x: new Date(c.date).getTime(), y: c.volume })),
        backgroundColor: props.candles.map(c => c.close >= c.open ? '#1D9E7566' : '#E24B4A66'),
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { type: 'time', time: { unit: 'month' }, ticks: { display: false }, grid: { display: false } },
        y: { grid: { color: '#f3f4f6' }, ticks: { font: { size: 10 }, maxTicksLimit: 3 } },
      },
    },
  })
}

watch(() => props.candles, buildChart)
onMounted(buildChart)
onUnmounted(() => { if (chart) chart.destroy() })
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-100 px-4 pb-2 pt-3">
    <p class="text-xs text-gray-400 mb-1">거래량</p>
    <div class="h-[80px]">
      <canvas ref="canvasRef" />
    </div>
  </div>
</template>

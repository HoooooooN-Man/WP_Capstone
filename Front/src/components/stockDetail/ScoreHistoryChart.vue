<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import {
  Chart as ChartJS, LineElement, PointElement, LinearScale, TimeScale,
  Filler, Tooltip,
} from 'chart.js'
import 'chartjs-adapter-date-fns'

ChartJS.register(LineElement, PointElement, LinearScale, TimeScale, Filler, Tooltip)

const props = defineProps({ history: { type: Array, default: () => [] } })
const canvasRef = ref(null)
let chart = null

// A/B 구역 배경 그리는 beforeDraw 플러그인
const zonePlugin = {
  id: 'tierZones',
  beforeDraw(ch) {
    const { ctx, chartArea: { left, right, top, bottom }, scales: { y } } = ch
    if (!y) return
    const toY = v => y.getPixelForValue(v)
    ctx.save()
    ctx.fillStyle = 'rgba(29,158,117,0.05)'
    ctx.fillRect(left, toY(80), right - left, toY(100) - toY(80))
    ctx.fillStyle = 'rgba(55,138,221,0.05)'
    ctx.fillRect(left, toY(60), right - left, toY(80) - toY(60))
    ctx.restore()
  },
}

function buildChart() {
  if (!canvasRef.value || !props.history.length) return
  if (chart) { chart.destroy(); chart = null }

  chart = new ChartJS(canvasRef.value, {
    type: 'line',
    data: {
      datasets: [{
        label: 'ML 점수',
        data: props.history.map(h => ({ x: new Date(h.date).getTime(), y: h.score })),
        borderColor: '#378ADD',
        backgroundColor: '#378ADD22',
        fill: true,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${ctx.raw.y.toFixed(1)}점` } },
      },
      scales: {
        x: { type: 'time', time: { unit: 'month' }, grid: { display: false } },
        y: { min: 0, max: 100, grid: { color: '#f3f4f6' }, ticks: { font: { size: 10 } } },
      },
    },
    plugins: [zonePlugin],
  })
}

watch(() => props.history, buildChart)
onMounted(buildChart)
onUnmounted(() => { if (chart) chart.destroy() })
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-100 p-4">
    <p class="text-xs font-medium text-gray-500 mb-2">ML 점수 추이</p>
    <div class="h-[160px]">
      <canvas ref="canvasRef" />
    </div>
  </div>
</template>

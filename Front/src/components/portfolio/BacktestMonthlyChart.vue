<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import {
  Chart as ChartJS, BarElement, LineElement, PointElement,
  CategoryScale, LinearScale, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(BarElement, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend)

const props = defineProps({ data: { type: Array, default: () => [] } })
const canvasRef = ref(null)
let chart = null

function buildChart() {
  if (!canvasRef.value || !props.data.length) return
  if (chart) { chart.destroy(); chart = null }

  const labels = props.data.map(d => d.month)
  const returns = props.data.map(d => d.return)
  const cumulative = props.data.map(d => d.cumulative_return)

  chart = new ChartJS(canvasRef.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          type: 'bar',
          label: '월별 수익률 (%)',
          data: returns,
          backgroundColor: returns.map(r => r >= 0 ? '#1D9E7566' : '#E24B4A66'),
          borderWidth: 0,
          yAxisID: 'y',
        },
        {
          type: 'line',
          label: '누적 수익률 (%)',
          data: cumulative,
          borderColor: '#378ADD',
          backgroundColor: 'transparent',
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 2,
          yAxisID: 'y1',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { position: 'top', labels: { font: { size: 11 } } },
        tooltip: { mode: 'index', intersect: false },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y:  { position: 'left',  grid: { color: '#f3f4f6' }, ticks: { font: { size: 10 } } },
        y1: { position: 'right', grid: { display: false }, ticks: { font: { size: 10 } } },
      },
    },
  })
}

watch(() => props.data, buildChart)
onMounted(buildChart)
onUnmounted(() => { if (chart) chart.destroy() })
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-100 p-4">
    <p class="text-xs font-medium text-gray-500 mb-3">월별 / 누적 수익률</p>
    <div class="h-[240px]">
      <canvas ref="canvasRef" />
    </div>
  </div>
</template>

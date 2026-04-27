<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, LineElement, PointElement, LinearScale, TimeScale,
  Tooltip, Legend,
} from 'chart.js'
import 'chartjs-adapter-date-fns'

ChartJS.register(LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend)

const props = defineProps({
  results:        { type: Array,  default: () => [] },
  colorMap:       { type: Object, default: () => ({}) },
  hiddenTickers:  { type: Object, default: () => new Set() }, // Set
})
const emit = defineEmits(['toggle-ticker'])

const chartData = computed(() => ({
  datasets: props.results
    .filter(r => !props.hiddenTickers.has(r.ticker))
    .map(r => ({
      label: `${r.name} (${r.ticker})`,
      data: r.score_history.map(h => ({ x: new Date(h.date).getTime(), y: h.score })),
      borderColor: props.colorMap[r.ticker],
      backgroundColor: 'transparent',
      tension: 0.2,
      pointRadius: 2,
      borderWidth: 2,
    })),
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: {
    legend: { display: false },
    tooltip: { mode: 'index', intersect: false },
  },
  scales: {
    x: {
      type: 'time',
      time: { unit: 'month' },
      grid: { display: false },
    },
    y: {
      min: 0, max: 100,
      title: { display: true, text: 'ML 점수', font: { size: 10 } },
      grid: { color: '#f3f4f6' },
      ticks: { font: { size: 10 } },
    },
  },
}
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-100 p-4 flex flex-col gap-3">
    <p class="text-xs font-medium text-gray-500">ML 점수 추이 비교</p>

    <div class="h-[280px]">
      <Line :data="chartData" :options="chartOptions" />
    </div>

    <!-- 커스텀 범례 -->
    <div class="flex flex-wrap gap-3">
      <button
        v-for="r in results"
        :key="r.ticker"
        class="flex items-center gap-1.5 text-xs transition-opacity"
        :class="hiddenTickers.has(r.ticker) ? 'opacity-40' : ''"
        @click="emit('toggle-ticker', r.ticker)"
      >
        <span class="w-3 h-3 rounded-sm" :style="{ backgroundColor: colorMap[r.ticker] }" />
        <span :class="hiddenTickers.has(r.ticker) ? 'line-through text-gray-400' : 'text-gray-700'">
          {{ r.name }}
        </span>
        <span class="font-mono text-gray-400">{{ r.ticker }}</span>
      </button>
    </div>
  </div>
</template>

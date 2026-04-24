<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS, BarElement, CategoryScale, LinearScale, Tooltip,
} from 'chart.js'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip)

const props = defineProps({
  items: { type: Array, default: () => [] },
})

// 10개 버킷 [0-10, 10-20, ..., 90-100]
const buckets = computed(() => {
  const b = Array(10).fill(0)
  props.items.forEach(item => {
    const idx = Math.min(Math.floor(item.score / 10), 9)
    b[idx]++
  })
  return b
})

// #E24B4A (low) → #1D9E75 (high)
const BUCKET_COLORS = [
  '#E24B4A', '#E5673B', '#E8822C', '#EB9E1D',
  '#C4A81F', '#9DB221', '#77BC23', '#50B63A',
  '#2EAD55', '#1D9E75',
]

const chartData = computed(() => ({
  labels: ['0', '10', '20', '30', '40', '50', '60', '70', '80', '90'],
  datasets: [{
    label: '종목 수',
    data: buckets.value,
    backgroundColor: BUCKET_COLORS,
    borderRadius: 3,
    borderWidth: 0,
  }],
}))

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: ctx => ` ${ctx.raw}종목` } },
  },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 10 } } },
    y: { grid: { color: '#f3f4f6' }, ticks: { font: { size: 10 }, maxTicksLimit: 5 } },
  },
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <p class="text-xs font-medium text-gray-500">점수 분포</p>
    <div class="h-[180px]">
      <Bar :data="chartData" :options="options" />
    </div>
  </div>
</template>

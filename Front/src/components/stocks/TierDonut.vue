<script setup>
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps({
  tierCounts: { type: Object, default: () => ({ A: 0, B: 0, C: 0, D: 0 }) },
})

const COLORS = { A: '#1D9E75', B: '#378ADD', C: '#EF9F27', D: '#E24B4A' }

const total = computed(() =>
  Object.values(props.tierCounts).reduce((s, n) => s + n, 0)
)

const centerTextPlugin = {
  id: 'centerText',
  afterDraw(chart) {
    const { ctx, chartArea: { width, height, left, top } } = chart
    ctx.save()
    ctx.font = 'bold 20px sans-serif'
    ctx.fillStyle = '#1f2937'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(total.value, left + width / 2, top + height / 2)
    ctx.restore()
  },
}

const chartData = computed(() => ({
  labels: ['A', 'B', 'C', 'D'],
  datasets: [{
    data: [
      props.tierCounts.A,
      props.tierCounts.B,
      props.tierCounts.C,
      props.tierCounts.D,
    ],
    backgroundColor: [COLORS.A, COLORS.B, COLORS.C, COLORS.D],
    borderWidth: 0,
    hoverOffset: 4,
  }],
}))

const options = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '68%',
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}종목` } },
  },
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="h-[200px]">
      <Doughnut :data="chartData" :options="options" :plugins="[centerTextPlugin]" />
    </div>
    <!-- 범례 -->
    <div class="grid grid-cols-2 gap-1.5">
      <div
        v-for="(val, tier) in tierCounts"
        :key="tier"
        class="flex items-center gap-1.5 text-xs"
      >
        <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: COLORS[tier] }" />
        <span class="text-gray-600">Tier {{ tier }}</span>
        <span class="font-medium text-gray-800 ml-auto">{{ val }}</span>
      </div>
    </div>
  </div>
</template>

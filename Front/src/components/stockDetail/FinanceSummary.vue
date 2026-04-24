<script setup>
import { computed } from 'vue'
import { Radar } from 'vue-chartjs'
import {
  Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const props = defineProps({
  latest:    { type: Object, default: null },
  scoreItem: { type: Object, default: null }, // latest score history item (with prob fields)
})

function gaugeColor(score) {
  if (!score) return '#e5e7eb'
  if (score >= 70) return '#1D9E75'
  if (score >= 40) return '#EF9F27'
  return '#E24B4A'
}

const radarData = computed(() => ({
  labels: ['LightGBM', 'XGBoost', 'CatBoost'],
  datasets: [{
    label: '모델별 확률',
    data: [
      (props.scoreItem?.prob_lgbm ?? 0) * 100,
      (props.scoreItem?.prob_xgb  ?? 0) * 100,
      (props.scoreItem?.prob_cat  ?? 0) * 100,
    ],
    backgroundColor: '#378ADD22',
    borderColor: '#378ADD',
    pointBackgroundColor: '#378ADD',
    borderWidth: 2,
  }],
}))

const radarOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    r: {
      min: 0, max: 100,
      ticks: { stepSize: 25, font: { size: 9 } },
      grid: { color: '#f3f4f6' },
    },
  },
  plugins: { legend: { display: false } },
}

const CARDS = computed(() => [
  { label: 'PER',       value: props.latest?.per?.toFixed(1)          ?? '-', suffix: '배' },
  { label: 'PBR',       value: props.latest?.pbr?.toFixed(2)          ?? '-', suffix: '배' },
  { label: 'ROE',       value: props.latest?.roe?.toFixed(1)          ?? '-', suffix: '%' },
  { label: '부채비율',   value: props.latest?.debt_ratio?.toFixed(1)   ?? '-', suffix: '%' },
  { label: '영업이익률', value: props.latest?.op_margin?.toFixed(1)    ?? '-', suffix: '%' },
  { label: '재무점수',   value: props.latest?.finance_score?.toFixed(1)?? '-', suffix: '점' },
])
</script>

<template>
  <div class="flex flex-col gap-5">

    <!-- 6 카드 -->
    <div class="grid grid-cols-3 gap-3">
      <div v-for="card in CARDS" :key="card.label" class="bg-gray-50 rounded-xl p-4">
        <p class="text-xs text-gray-400 mb-1">{{ card.label }}</p>
        <p class="text-xl font-medium text-gray-900">
          {{ card.value }}<span class="text-sm text-gray-400 ml-0.5">{{ card.value !== '-' ? card.suffix : '' }}</span>
        </p>
      </div>
    </div>

    <!-- 재무점수 게이지 -->
    <div>
      <div class="flex items-center justify-between text-xs text-gray-500 mb-1.5">
        <span>재무점수</span>
        <span class="font-medium text-gray-800">{{ latest?.finance_score?.toFixed(1) ?? '-' }}점</span>
      </div>
      <div class="h-2 rounded bg-gray-200 overflow-hidden">
        <div
          class="h-full rounded transition-all"
          :style="{ width: (latest?.finance_score ?? 0) + '%', backgroundColor: gaugeColor(latest?.finance_score) }"
        />
      </div>
    </div>

    <!-- 레이더 차트 -->
    <div>
      <p class="text-xs font-medium text-gray-500 mb-2">모델별 확률</p>
      <div class="h-[200px]">
        <Radar :data="radarData" :options="radarOptions" />
      </div>
    </div>

  </div>
</template>

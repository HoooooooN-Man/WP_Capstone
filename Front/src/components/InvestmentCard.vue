<template>
  <div
    class="investment-card relative w-72 h-96 perspective-1000"
    :class="{ 'ring-glow': isRisk }"
    @click="toggleFlip"
  >
    <div
      class="card-inner relative w-full h-full duration-500 transform-style-preserve-3d"
      :class="{ 'rotate-y-180': flipped }"
    >
      <!-- Front -->
      <div class="card-face card-front absolute inset-0 bg-white rounded-xl shadow-2xl overflow-hidden border border-slate-200">
        <div class="h-12 flex items-center px-3 border-b border-slate-100">
          <LucideCircle class="text-amber-500" :size="20" />
          <span class="ml-2 font-bold text-sm">단어장 고리</span>
        </div>
        <div class="p-4 h-60 grid gap-2">
          <div class="text-xs text-slate-500">종목명</div>
          <h2 class="font-bold text-2xl truncate">{{ stockName }}</h2>

          <div class="grid grid-cols-2 gap-3 mt-4">
            <div class="p-2 rounded-lg bg-slate-100">
              <div class="text-xs text-slate-500">현재가</div>
              <div class="text-lg font-semibold">{{ formattedPrice }}</div>
            </div>
            <div class="p-2 rounded-lg" :class="scoreColorClass">
              <div class="text-xs text-slate-500">퀀트 스코어</div>
              <div class="text-lg font-semibold">{{ score }}</div>
            </div>
          </div>

          <div class="p-2 mt-2 rounded-lg bg-slate-50 text-xs text-slate-600">
            <span class="font-semibold">위험 등급:</span>
            <span>{{ isRisk ? 'High Risk' : 'Low Risk' }}</span>
          </div>
        </div>

        <div class="absolute bottom-3 left-3 right-3 text-xs text-slate-400">
          클릭하면 플립 | 오른쪽으로 스와이프 시 매도(Swap)
        </div>
      </div>

      <!-- Back -->
      <div class="card-face card-back absolute inset-0 bg-slate-950 text-white rounded-xl shadow-2xl transform rotate-y-180 backface-hidden overflow-hidden">
        <div class="h-12 flex items-center px-3 border-b border-slate-800">
          <LucidePieChart class="text-white" :size="20" />
          <span class="ml-2 font-semibold text-sm">재무 요약 / 레이더</span>
        </div>

        <div class="p-3 h-[80%]">
          <Radar :data="chartData" :options="chartOptions" class="h-full" />
        </div>

        <ul class="px-4 pb-3 text-xs text-slate-300 space-y-1">
          <li>• EPS: 5.2</li>
          <li>• PER: 18.4</li>
          <li>• ROE: 14.8%</li>
          <li>• 부채비율: 95%</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { Radar } from 'vue-chartjs';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { LucideCircle, LucidePieChart } from 'lucide-vue-next';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const props = defineProps({
  stockName: { type: String, required: true },
  price: { type: Number, required: true },
  score: { type: Number, required: true },
  isRisk: { type: Boolean, default: false },
});

const flipped = ref(false);

const toggleFlip = () => {
  flipped.value = !flipped.value;
};

const formattedPrice = computed(() => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency', currency: 'KRW', maximumFractionDigits: 0,
  }).format(props.price);
});

const scoreColorClass = computed(() => {
  if (props.score >= 80) return 'bg-emerald-500 text-white';
  if (props.score >= 50) return 'bg-amber-500 text-white';
  return 'bg-rose-500 text-white';
});

const chartData = computed(() => ({
  labels: ['밸류', '성장', '안정성', '수익성', '시장성'],
  datasets: [{
    label: props.stockName,
    data: [props.score, Math.max(10, props.score - 8), Math.max(10, 100 - props.score), props.score * 0.85, props.score * 0.9],
    backgroundColor: 'rgba(34, 197, 94, 0.3)',
    borderColor: 'rgb(34, 197, 94)',
    pointBackgroundColor: 'rgb(34, 197, 94)',
    borderWidth: 2,
    fill: true,
  }],
}));

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    r: {
      suggestedMin: 0,
      suggestedMax: 100,
      grid: { color: 'rgba(148, 163, 184, 0.3)' },
      angleLines: { color: 'rgba(148, 163, 184, 0.3)' },
      pointLabels: { color: '#cbd5e1', font: { size: 12 } },
      ticks: { color: '#94a3b8', backdropColor: 'transparent' },
    },
  },
  plugins: {
    legend: { display: false },
    tooltip: { enabled: true },
  },
};
</script>

<style scoped>
.perspective-1000 { perspective: 1000px; }
.transform-style-preserve-3d { transform-style: preserve-3d; }
.backface-hidden { backface-visibility: hidden; }
.card-inner { transition: transform 0.6s; }
.rotate-y-180 { transform: rotateY(180deg); }
.card-face { backface-visibility: hidden; }
.ring-glow { box-shadow: 0 0 12px 3px rgba(239, 68, 68, 0.8); }
</style>

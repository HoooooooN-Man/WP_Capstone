<script setup>
import { useRouter } from 'vue-router'
import TierBadge from '@/components/common/TierBadge.vue'

const props = defineProps({
  stock: { type: Object, default: null },
  open:  { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const router = useRouter()

const MODELS = [
  { key: 'prob_lgbm', label: 'LightGBM' },
  { key: 'prob_xgb',  label: 'XGBoost' },
  { key: 'prob_cat',  label: 'CatBoost' },
]

function goDetail() {
  router.push('/stocks/' + props.stock?.ticker)
  emit('close')
}
</script>

<template>
  <!-- 백드롭 -->
  <Transition name="fade">
    <div
      v-if="open"
      class="fixed inset-0 bg-black/20 z-40"
      @click="emit('close')"
    />
  </Transition>

  <!-- 드로어 -->
  <Transition name="slide">
    <aside
      v-if="open"
      class="fixed right-0 top-0 h-full w-80 bg-white shadow-lg z-50 flex flex-col"
    >
      <!-- 헤더 -->
      <div class="flex items-start justify-between px-5 pt-5 pb-4 border-b border-gray-100">
        <div>
          <p class="text-base font-medium text-gray-900">{{ stock?.name }}</p>
          <p class="text-sm text-gray-400 mt-0.5">
            {{ stock?.ticker }} · {{ stock?.sector }}
          </p>
        </div>
        <button class="text-gray-400 hover:text-gray-700 transition-colors" @click="emit('close')">
          ✕
        </button>
      </div>

      <!-- 바디 -->
      <div class="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-5">

        <!-- 모델별 확률 -->
        <div>
          <p class="text-xs font-medium text-gray-500 mb-3">앙상블 확률 상세</p>
          <div class="flex flex-col gap-3">
            <div v-for="m in MODELS" :key="m.key" class="flex items-center gap-2.5">
              <span class="text-xs text-gray-500 w-20 shrink-0">{{ m.label }}</span>
              <div class="flex-1 h-1.5 rounded bg-gray-200 overflow-hidden">
                <div
                  class="h-full rounded"
                  style="background-color: #378ADD"
                  :style="{ width: ((stock?.[m.key] ?? 0) * 100) + '%' }"
                />
              </div>
              <span class="text-xs font-medium w-10 text-right">
                {{ ((stock?.[m.key] ?? 0) * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>

        <hr class="border-gray-100" />

        <!-- 앙상블 평균 -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-600">앙상블 평균</span>
          <span class="text-sm font-semibold text-blue-600">
            {{ ((stock?.prob_ensemble ?? 0) * 100).toFixed(1) }}%
          </span>
        </div>

        <!-- ML 점수 -->
        <div>
          <p class="text-xs font-medium text-gray-500 mb-2">ML 점수</p>
          <div class="flex items-center gap-2">
            <span class="text-2xl font-bold text-gray-900">{{ Math.round(stock?.score ?? 0) }}</span>
            <span class="text-sm text-gray-400">/ 100</span>
            <TierBadge v-if="stock?.tier" :tier="stock.tier" />
          </div>
          <p class="text-xs text-gray-400 mt-1">
            전체 {{ stock?.total_in_date }}종목 중 {{ stock?.rank_in_date }}위
          </p>
        </div>

      </div>

      <!-- 푸터 -->
      <div class="px-5 py-4 border-t border-gray-100">
        <button
          class="w-full bg-gray-900 text-white text-sm rounded-lg py-2.5 hover:bg-gray-700 transition-colors"
          @click="goDetail"
        >
          종목 상세 보기
        </button>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active, .slide-leave-active { transition: transform 0.25s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
</style>

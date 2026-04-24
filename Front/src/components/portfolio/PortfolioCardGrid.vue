<script setup>
import { useRouter } from 'vue-router'
import TierBadge from '@/components/common/TierBadge.vue'

defineProps({
  items:   { type: Array,   default: () => [] },
  type:    { type: String,  default: 'growth' },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
})

const router = useRouter()

const BAR_COLORS = { A: '#1D9E75', B: '#378ADD', C: '#EF9F27', D: '#E24B4A' }
function barColor(score) {
  if (score >= 80) return BAR_COLORS.A
  if (score >= 60) return BAR_COLORS.B
  if (score >= 40) return BAR_COLORS.C
  return BAR_COLORS.D
}
</script>

<template>
  <!-- 에러 상태 -->
  <div
    v-if="error === 'not_ready'"
    class="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-700"
  >
    <template v-if="type === 'stable'">
      현재 PBR 재무 데이터가 준비중입니다.<br>
      데이터 준비 완료 후 이용 가능합니다.
    </template>
    <template v-else>
      KOSPI 추천 데이터가 준비중입니다.
    </template>
  </div>

  <div
    v-else-if="error && error !== 'not_ready'"
    class="text-center text-gray-500 py-8"
  >
    데이터를 불러오지 못했습니다
  </div>

  <!-- 로딩 스켈레톤 -->
  <div v-else-if="loading" class="grid grid-cols-2 gap-3">
    <div
      v-for="i in 10"
      :key="i"
      class="h-28 bg-gray-100 rounded-xl animate-pulse"
    />
  </div>

  <!-- 카드 그리드 -->
  <div v-else class="grid grid-cols-2 gap-3">
    <div
      v-for="item in items"
      :key="item.ticker"
      class="bg-white border border-gray-100 rounded-xl p-4 cursor-pointer hover:bg-gray-50 transition-colors flex flex-col gap-2"
      @click="router.push('/stocks/' + item.ticker)"
    >
      <!-- 상단: 순위 + Tier -->
      <div class="flex items-center justify-between">
        <span class="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-600">
          {{ item.rank }}
        </span>
        <TierBadge :tier="item.tier" />
      </div>

      <!-- 종목명 + 코드 -->
      <div>
        <p class="text-base font-medium text-gray-900">{{ item.name }}</p>
        <p class="font-mono text-xs text-gray-400">{{ item.ticker }}</p>
      </div>

      <!-- 하단: 섹터 + 점수 -->
      <div class="flex items-center justify-between">
        <span class="bg-gray-100 text-gray-500 text-xs rounded-full px-2 py-0.5">{{ item.sector }}</span>
        <div class="flex items-center gap-1.5">
          <div class="w-20 h-1.5 rounded bg-gray-200 overflow-hidden">
            <div
              class="h-full rounded"
              :style="{ width: item.score + '%', backgroundColor: barColor(item.score) }"
            />
          </div>
          <span class="text-xs font-medium text-gray-700">{{ Math.round(item.score) }}</span>
        </div>
      </div>

      <!-- PBR (안정형만) -->
      <div v-if="type === 'stable' && item.pbr != null" class="flex items-center gap-1">
        <span class="text-xs text-gray-400">PBR</span>
        <span class="text-xs font-medium text-blue-600">{{ item.pbr.toFixed(2) }}</span>
      </div>
    </div>
  </div>
</template>

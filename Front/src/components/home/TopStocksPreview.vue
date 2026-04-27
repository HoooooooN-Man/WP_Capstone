<script setup>
import { useRouter } from 'vue-router'
import TierBadge from '@/components/common/TierBadge.vue'

defineProps({
  items: { type: Array, default: () => [] },
})

const router = useRouter()

function barColor(score) {
  if (score >= 80) return '#1D9E75'
  if (score >= 60) return '#378ADD'
  if (score >= 40) return '#EF9F27'
  return '#E24B4A'
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div
      v-for="(item, idx) in items"
      :key="item.ticker"
      class="flex items-center gap-3 rounded-lg border border-gray-100 px-3 py-2.5 cursor-pointer hover:bg-gray-50 transition-colors"
      @click="router.push('/stocks/' + item.ticker)"
    >
      <!-- 순위 -->
      <span class="w-5 text-xs text-gray-400 text-center shrink-0">{{ idx + 1 }}</span>

      <!-- 종목명 + 티커 -->
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-gray-900 truncate">{{ item.name }}</p>
        <p class="text-xs text-gray-400 font-mono">{{ item.ticker }}</p>
      </div>

      <!-- 점수 바 + 숫자 + 배지 -->
      <div class="flex items-center gap-2 shrink-0">
        <div class="w-24 h-1.5 rounded bg-gray-200 overflow-hidden">
          <div
            class="h-full rounded"
            :style="{ width: item.score + '%', backgroundColor: barColor(item.score) }"
          />
        </div>
        <span class="text-sm font-medium w-8 text-right">{{ Math.round(item.score) }}</span>
        <TierBadge :tier="item.tier" />
      </div>
    </div>

    <div v-if="!items.length" class="text-center text-gray-400 py-6 text-sm">
      데이터 없음
    </div>
  </div>
</template>

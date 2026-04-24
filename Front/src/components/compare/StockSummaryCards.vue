<script setup>
import { useRouter } from 'vue-router'
import TierBadge from '@/components/common/TierBadge.vue'

defineProps({
  results:  { type: Array,  default: () => [] },
  colorMap: { type: Object, default: () => ({}) },
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
  <div class="flex gap-3 flex-wrap">
    <div
      v-for="r in results"
      :key="r.ticker"
      class="w-44 bg-white border border-gray-100 rounded-xl p-4 cursor-pointer hover:bg-gray-50 transition-colors flex flex-col gap-2 border-l-4"
      :style="{ borderLeftColor: colorMap[r.ticker] }"
      @click="router.push('/stocks/' + r.ticker)"
    >
      <div>
        <p class="font-mono text-xs text-gray-400">{{ r.ticker }}</p>
        <p class="font-medium text-sm text-gray-900 truncate mt-0.5">{{ r.name }}</p>
        <p class="text-xs text-gray-400 mt-0.5">{{ r.sector }}</p>
      </div>
      <hr class="border-gray-100" />
      <div class="flex items-center gap-2">
        <div class="flex-1 h-1.5 rounded bg-gray-200 overflow-hidden">
          <div
            class="h-full rounded"
            :style="{ width: (r.latest_score ?? 0) + '%', backgroundColor: barColor(r.latest_score ?? 0) }"
          />
        </div>
        <span class="text-xs font-medium">{{ Math.round(r.latest_score ?? 0) }}</span>
      </div>
      <TierBadge :tier="r.tier" />
    </div>
  </div>
</template>

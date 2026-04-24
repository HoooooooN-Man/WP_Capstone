<script setup>
import { useRouter } from 'vue-router'
import TierBadge from '@/components/common/TierBadge.vue'

const props = defineProps({
  item: { type: Object, required: true },
  rank: { type: Number, required: true },
})
const emit = defineEmits(['click'])
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
  <tr
    class="border-t border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
    @click="emit('click', item)"
  >
    <td class="px-3 py-2.5 text-xs text-gray-400 w-8">{{ rank }}</td>
    <td class="px-3 py-2.5 font-mono text-xs text-gray-400">{{ item.ticker }}</td>
    <td class="px-3 py-2.5 font-medium text-sm text-gray-900">{{ item.name }}</td>
    <td class="px-3 py-2.5">
      <span class="bg-gray-100 text-gray-500 text-xs rounded-full px-2 py-0.5">{{ item.sector }}</span>
    </td>
    <td class="px-3 py-2.5 text-sm text-right text-gray-700">{{ item.close?.toLocaleString() }}원</td>
    <td class="px-3 py-2.5">
      <div class="flex items-center gap-2">
        <div class="w-20 h-1.5 rounded bg-gray-200 overflow-hidden">
          <div
            class="h-full rounded"
            :style="{ width: item.score + '%', backgroundColor: barColor(item.score) }"
          />
        </div>
        <span class="text-sm font-medium w-8 text-right">{{ Math.round(item.score) }}</span>
      </div>
    </td>
    <td class="px-3 py-2.5"><TierBadge :tier="item.tier" /></td>
    <td class="px-3 py-2.5">
      <button
        class="text-xs text-gray-400 hover:text-gray-700 border border-gray-200 rounded-md px-2 py-1 transition-colors"
        @click.stop="router.push('/stocks/' + item.ticker)"
      >
        상세
      </button>
    </td>
  </tr>
</template>

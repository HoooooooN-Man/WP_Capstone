<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['sector-click'])

const sorted = computed(() =>
  [...props.items].sort((a, b) => b.avg_score - a.avg_score)
)

function dotColor(score) {
  if (score >= 70) return '#1D9E75'
  if (score >= 50) return '#EF9F27'
  return '#E24B4A'
}
</script>

<template>
  <div class="overflow-auto rounded-xl border border-gray-100">
    <table class="w-full text-sm">
      <thead class="bg-gray-50 sticky top-0">
        <tr>
          <th class="text-left text-xs text-gray-500 font-medium px-4 py-2.5">섹터</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">종목수</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">평균점수</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">최고점수</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">Tier A</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in sorted"
          :key="item.sector"
          class="border-t border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
          @click="emit('sector-click', item.sector)"
        >
          <td class="px-4 py-2.5 font-medium text-gray-800">{{ item.sector }}</td>
          <td class="px-4 py-2.5 text-right text-gray-500">{{ item.stock_count }}</td>
          <td class="px-4 py-2.5 text-right">
            <span class="inline-flex items-center gap-1.5">
              <span
                class="w-2 h-2 rounded-full inline-block"
                :style="{ backgroundColor: dotColor(item.avg_score) }"
              />
              {{ item.avg_score.toFixed(1) }}
            </span>
          </td>
          <td class="px-4 py-2.5 text-right text-gray-500">{{ item.max_score.toFixed(1) }}</td>
          <td class="px-4 py-2.5 text-right text-gray-500">{{ item.tier_a_count }}</td>
        </tr>
        <tr v-if="!items.length">
          <td colspan="5" class="text-center text-gray-400 py-8">데이터 없음</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

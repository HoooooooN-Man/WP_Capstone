<script setup>
import TierDonut       from './TierDonut.vue'
import ScoreHistogram  from './ScoreHistogram.vue'

defineProps({
  tierCounts: { type: Object, default: () => ({ A: 0, B: 0, C: 0, D: 0 }) },
  items:      { type: Array,  default: () => [] },
})
</script>

<template>
  <aside class="sticky top-6 flex flex-col gap-4">
    <div class="bg-white border border-gray-200 rounded-xl p-4">
      <p class="text-xs font-medium text-gray-500 mb-3">Tier 분포</p>
      <TierDonut :tier-counts="tierCounts" />
    </div>
    <div class="bg-white border border-gray-200 rounded-xl p-4">
      <ScoreHistogram :items="items" />
    </div>
  </aside>
</template>

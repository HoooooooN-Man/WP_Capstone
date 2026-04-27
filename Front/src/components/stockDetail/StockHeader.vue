<script setup>
import TierBadge from '@/components/common/TierBadge.vue'

defineProps({
  ticker:      { type: String, default: '' },
  name:        { type: String, default: '' },
  sector:      { type: String, default: '' },
  midSector:   { type: String, default: '' },
  latestScore: { type: Number, default: 0 },
  latestTier:  { type: String, default: 'D' },
  isFavorite:  { type: Boolean, default: false },
})
defineEmits(['toggle-favorite'])
</script>

<template>
  <div class="flex items-start justify-between py-4">

    <!-- 좌측: 종목명 + 태그 -->
    <div class="flex flex-col gap-2">
      <h1 class="text-2xl font-medium text-gray-900">{{ name }}</h1>
      <div class="flex items-center gap-2 flex-wrap">
        <span class="font-mono text-sm text-gray-400">{{ ticker }}</span>
        <span class="bg-gray-100 text-gray-500 text-xs rounded-full px-2 py-0.5">{{ sector }}</span>
        <span v-if="midSector" class="bg-gray-100 text-gray-500 text-xs rounded-full px-2 py-0.5">{{ midSector }}</span>
      </div>
    </div>

    <!-- 우측: ML 점수 + 관심종목 -->
    <div class="flex flex-col items-end gap-2">
      <p class="text-xs text-gray-400">ML 점수</p>
      <div class="flex items-center gap-2">
        <span class="text-3xl font-medium text-gray-900">{{ Math.round(latestScore) }}</span>
        <span class="text-sm text-gray-400">/ 100</span>
        <TierBadge :tier="latestTier" />
      </div>
      <button
        class="flex items-center gap-1.5 text-sm border rounded-lg px-3 py-1.5 transition-colors"
        :class="isFavorite
          ? 'border-red-200 text-red-500 bg-red-50 hover:bg-red-100'
          : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
        @click="$emit('toggle-favorite')"
      >
        {{ isFavorite ? '♥' : '♡' }}
        <span>{{ isFavorite ? '관심종목' : '관심종목 추가' }}</span>
      </button>
    </div>

  </div>
</template>

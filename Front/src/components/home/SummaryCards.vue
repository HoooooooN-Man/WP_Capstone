<script setup>
defineProps({
  regime: { type: Object, default: null },
})
</script>

<template>
  <div class="grid grid-cols-3 gap-3">
    <div class="bg-gray-50 rounded-xl p-4">
      <p class="text-xs text-gray-500 mb-1">분석 종목 수</p>
      <p class="text-2xl font-medium text-gray-900">
        {{ regime ? regime.total_count.toLocaleString() : '—' }}
        <span class="text-sm font-normal text-gray-500">종목</span>
      </p>
    </div>
    <div class="bg-gray-50 rounded-xl p-4">
      <p class="text-xs text-gray-500 mb-1">Tier A 종목</p>
      <p class="text-2xl font-medium text-gray-900">
        {{ regime?.tier_a_count ?? '—' }}
        <span class="text-sm font-normal text-gray-500">종목</span>
      </p>
    </div>
    <div class="bg-gray-50 rounded-xl p-4">
      <p class="text-xs text-gray-500 mb-1">Tier A 비율</p>
      <p class="text-2xl font-medium text-gray-900">
        {{ regime ? (regime.tier_a_ratio * 100).toFixed(1) : '—' }}
        <span class="text-sm font-normal text-gray-500">%</span>
      </p>
    </div>
  </div>
</template>

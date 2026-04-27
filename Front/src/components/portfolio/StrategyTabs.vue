<script setup>
defineProps({
  activeType:      { type: String, default: 'growth' },
  versions:        { type: Array,  default: () => [] },
  selectedVersion: { type: String, default: 'latest' },
  currentDate:     { type: String, default: null },
})
defineEmits(['type-change', 'version-change'])
</script>

<template>
  <div class="flex items-center justify-between">

    <!-- 좌측: 전략 탭 -->
    <div class="flex gap-2">
      <button
        v-for="t in [{ value: 'growth', label: '성장형' }, { value: 'stable', label: '안정형' }]"
        :key="t.value"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        :class="activeType === t.value
          ? 'bg-gray-900 text-white'
          : 'border border-gray-200 text-gray-500 hover:bg-gray-50'"
        @click="$emit('type-change', t.value)"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 우측: 버전 선택 + 날짜 -->
    <div class="flex items-center gap-3">
      <select
        :value="selectedVersion"
        class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
        @change="$emit('version-change', $event.target.value)"
      >
        <option value="latest">최신 버전</option>
        <option v-for="v in versions" :key="v" :value="v">{{ v }}</option>
      </select>
      <span v-if="currentDate" class="text-sm text-gray-400">기준일 {{ currentDate }}</span>
    </div>

  </div>
</template>

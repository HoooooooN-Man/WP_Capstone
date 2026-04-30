<script setup>
defineProps({
  regime:          { type: Object,  default: null },
  versions:        { type: Array,   default: () => [] },
  dates:           { type: Array,   default: () => [] },
  selectedVersion: { type: String,  default: 'latest' },
  selectedDate:    { type: String,  default: '' },
})
const emit = defineEmits(['update:selectedVersion', 'update:selectedDate'])

const bgColor = { greed: '#EAF3DE', neutral: '#F1EFE8', fear: '#FCEBEB' }
const statusLabel = { greed: '강세장', neutral: '중립', fear: '약세장' }
</script>

<template>
  <div
    class="w-full rounded-xl px-6 py-5 flex flex-wrap items-center gap-4"
    :style="{ backgroundColor: bgColor[regime?.status] ?? '#F1EFE8' }"
  >
    <!-- 날씨 & 메시지 -->
    <div class="flex-1 min-w-0">
      <p class="text-2xl font-semibold text-gray-800 leading-tight">
        {{ regime?.weather ?? '—' }}
        <span class="text-base font-normal text-gray-500 ml-2">{{ statusLabel[regime?.status] ?? '' }}</span>
      </p>
      <p class="text-sm text-gray-500 mt-1">{{ regime?.message ?? '데이터를 불러오는 중입니다.' }}</p>
    </div>

    <!-- Tier A 비율 -->
    <div class="text-center px-4">
      <p class="text-4xl font-bold text-gray-800">
        {{ regime ? regime.tier_a_ratio.toFixed(1) : '—' }}<span class="text-xl font-normal">%</span>
      </p>
      <p class="text-xs text-gray-500 mt-1">Tier A 비율</p>
    </div>

    <!-- 필터 선택 -->
    <div class="flex flex-col gap-1.5 shrink-0">
      <select
        :value="selectedVersion"
        class="text-xs border border-gray-200 rounded-md px-2 py-1.5 bg-white focus:outline-none"
        @change="emit('update:selectedVersion', $event.target.value)"
      >
        <option value="latest">최신 버전</option>
        <option v-for="v in versions" :key="v" :value="v">{{ v }}</option>
      </select>
      <select
        :value="selectedDate"
        class="text-xs border border-gray-200 rounded-md px-2 py-1.5 bg-white focus:outline-none"
        @change="emit('update:selectedDate', $event.target.value)"
      >
        <option v-for="d in [...dates].reverse()" :key="d" :value="d">{{ d }}</option>
      </select>
      <p class="text-xs text-gray-400 text-right">기준일: {{ regime?.date ?? '—' }}</p>
    </div>
  </div>
</template>

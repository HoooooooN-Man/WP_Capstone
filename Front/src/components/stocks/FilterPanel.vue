<script setup>
import { computed } from 'vue'

const props = defineProps({
  versions: { type: Array,  default: () => [] },
  dates:    { type: Array,  default: () => [] },
  filters:  { type: Object, required: true },
})
const emit = defineEmits(['filter-change', 'reset'])

const SECTORS = [
  'IT', '헬스케어', '금융', '경기소비재', '필수소비재',
  '산업재', '에너지', '소재', '유틸리티', '부동산', '커뮤니케이션서비스',
]

const TIERS = [
  { label: 'A (80+)', min: 80 },
  { label: 'B (60+)', min: 60 },
  { label: 'C (40+)', min: 40 },
  { label: '전체',    min: 0  },
]

const reversedDates = computed(() => [...props.dates].reverse())

function change(key, value) {
  emit('filter-change', { key, value })
}
</script>

<template>
  <aside class="sticky top-6 bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-5 text-sm">

    <!-- 모델 버전 -->
    <div class="flex flex-col gap-1.5">
      <label class="text-xs font-medium text-gray-500">모델 버전</label>
      <select
        :value="filters.model_version"
        class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
        @change="change('model_version', $event.target.value)"
      >
        <option value="latest">최신 버전</option>
        <option v-for="v in versions" :key="v" :value="v">{{ v }}</option>
      </select>
    </div>

    <!-- 기준일 -->
    <div class="flex flex-col gap-1.5">
      <label class="text-xs font-medium text-gray-500">기준일</label>
      <select
        :value="filters.date"
        class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
        @change="change('date', $event.target.value)"
      >
        <option v-for="d in reversedDates" :key="d" :value="d">{{ d }}</option>
      </select>
    </div>

    <!-- 섹터 -->
    <div class="flex flex-col gap-1.5">
      <label class="text-xs font-medium text-gray-500">섹터</label>
      <select
        :value="filters.sector ?? ''"
        class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none"
        @change="change('sector', $event.target.value || null)"
      >
        <option value="">전체</option>
        <option v-for="s in SECTORS" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>

    <!-- 최소 점수 슬라이더 -->
    <div class="flex flex-col gap-1.5">
      <div class="flex items-center justify-between">
        <label class="text-xs font-medium text-gray-500">최소 점수</label>
        <span class="text-xs text-gray-700 font-medium">{{ filters.min_score }}점</span>
      </div>
      <input
        type="range"
        min="0" max="100" step="1"
        :value="filters.min_score"
        class="w-full accent-gray-700"
        @input="change('min_score', Number($event.target.value))"
      />
      <div class="flex justify-between text-xs text-gray-300">
        <span>0</span><span>50</span><span>100</span>
      </div>
    </div>

    <!-- Tier 빠른 선택 -->
    <div class="flex flex-col gap-1.5">
      <label class="text-xs font-medium text-gray-500">Tier 빠른 선택</label>
      <div class="grid grid-cols-2 gap-1.5">
        <button
          v-for="t in TIERS"
          :key="t.min"
          class="px-2 py-1.5 text-xs rounded-lg border transition-colors"
          :class="filters.min_score === t.min
            ? 'bg-gray-100 border-gray-400 font-medium text-gray-900'
            : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
          @click="change('min_score', t.min)"
        >
          {{ t.label }}
        </button>
      </div>
    </div>

    <!-- 초기화 -->
    <button
      class="text-xs text-red-400 hover:text-red-600 text-left transition-colors mt-auto pt-2 border-t border-gray-100"
      @click="emit('reset')"
    >
      필터 초기화
    </button>

  </aside>
</template>

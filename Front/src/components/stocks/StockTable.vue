<script setup>
import { ref, computed } from 'vue'
import StockRow from './StockRow.vue'

const props = defineProps({
  items:   { type: Array,  default: () => [] },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
})
const emit = defineEmits(['row-click'])

const sortAsc = ref(false)

const sorted = computed(() => {
  const list = [...props.items]
  list.sort((a, b) => sortAsc.value ? a.score - b.score : b.score - a.score)
  return list
})

function toggleSort() { sortAsc.value = !sortAsc.value }
</script>

<template>
  <div class="relative overflow-auto rounded-xl border border-gray-100 bg-white">

    <!-- 로딩 오버레이 -->
    <div
      v-if="loading"
      class="absolute inset-0 flex items-center justify-center bg-white/70 z-10 rounded-xl"
    >
      <div class="w-6 h-6 border-2 border-gray-300 border-t-gray-700 rounded-full animate-spin" />
    </div>

    <!-- 빈 상태 -->
    <div
      v-else-if="error === 'no_data' || (!loading && !items.length)"
      class="flex flex-col items-center justify-center py-16 gap-1"
    >
      <p class="text-gray-500">해당 조건에 맞는 종목이 없습니다</p>
      <p class="text-sm text-gray-400">필터를 완화해 보세요</p>
    </div>

    <!-- 에러 -->
    <div
      v-else-if="error === 'error'"
      class="flex items-center justify-center py-16 text-gray-500"
    >
      데이터를 불러오지 못했습니다
    </div>

    <!-- 테이블 -->
    <table v-else class="w-full text-sm">
      <thead class="bg-gray-50 sticky top-0">
        <tr>
          <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">순위</th>
          <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">종목코드</th>
          <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">종목명</th>
          <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">섹터</th>
          <th class="text-right text-xs text-gray-500 font-medium px-3 py-2.5">종가</th>
          <th
            class="text-left text-xs text-gray-500 font-medium px-3 py-2.5 cursor-pointer select-none"
            @click="toggleSort"
          >
            점수 {{ sortAsc ? '↑' : '↓' }}
          </th>
          <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">Tier</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <StockRow
          v-for="(item, idx) in sorted"
          :key="item.ticker"
          :item="item"
          :rank="idx + 1"
          @click="emit('row-click', item)"
        />
      </tbody>
    </table>
  </div>
</template>

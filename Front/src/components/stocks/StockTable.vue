<script setup>
import { ref, computed } from 'vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import { useThemeStore } from '@/stores/theme.js'
import StockRow from './StockRow.vue'

const props = defineProps({
  items:   { type: Array,  default: () => [] },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
})
const emit = defineEmits(['row-click'])

const theme   = useThemeStore()
const sortAsc = ref(false)

const sorted = computed(() => {
  const list = [...props.items]
  list.sort((a, b) => sortAsc.value ? a.score - b.score : b.score - a.score)
  return list.map((item, idx) => ({ ...item, _rank: idx + 1 }))
})

// 100개 이상이면 가상 스크롤 활성화
const useVirtual = computed(() => sorted.value.length >= 100)
const ROW_H = 48  // px

function toggleSort() { sortAsc.value = !sortAsc.value }
</script>

<template>
  <div
    class="relative overflow-auto rounded-xl border"
    :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
  >
    <!-- 로딩 오버레이 -->
    <div
      v-if="loading"
      class="absolute inset-0 flex items-center justify-center z-10 rounded-xl"
      :class="theme.isDark ? 'bg-[#1A1D27]/70' : 'bg-white/70'"
    >
      <div class="w-6 h-6 border-2 border-gray-300 border-t-gray-700 rounded-full animate-spin" />
    </div>

    <!-- 빈 상태 -->
    <div
      v-else-if="error === 'no_data' || (!loading && !items.length)"
      class="flex flex-col items-center justify-center py-16 gap-1"
    >
      <p :class="theme.isDark ? 'text-gray-500' : 'text-gray-500'">해당 조건에 맞는 종목이 없습니다</p>
      <p class="text-sm" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">필터를 완화해 보세요</p>
    </div>

    <!-- 에러 -->
    <div
      v-else-if="error === 'error'"
      class="flex items-center justify-center py-16"
      :class="theme.isDark ? 'text-gray-500' : 'text-gray-500'"
    >
      데이터를 불러오지 못했습니다
    </div>

    <!-- 테이블 -->
    <table v-else class="w-full text-sm">
      <thead class="sticky top-0 z-10" :class="theme.isDark ? 'bg-[#0F1117]' : 'bg-gray-50'">
        <tr>
          <th class="text-left text-xs font-medium px-3 py-2.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-500'">순위</th>
          <th class="text-left text-xs font-medium px-3 py-2.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-500'">종목코드</th>
          <th class="text-left text-xs font-medium px-3 py-2.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-500'">종목명</th>
          <th class="text-left text-xs font-medium px-3 py-2.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-500'">섹터</th>
          <th class="text-right text-xs font-medium px-3 py-2.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-500'">종가</th>
          <th
            class="text-left text-xs font-medium px-3 py-2.5 cursor-pointer select-none"
            :class="theme.isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-500 hover:text-gray-800'"
            @click="toggleSort"
          >
            점수 {{ sortAsc ? '↑' : '↓' }}
          </th>
          <th class="text-left text-xs font-medium px-3 py-2.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-500'">Tier</th>
          <th />
        </tr>
      </thead>

      <!-- 100개 미만: 일반 렌더 -->
      <tbody v-if="!useVirtual">
        <StockRow
          v-for="item in sorted"
          :key="item.ticker"
          :item="item"
          :rank="item._rank"
          @click="emit('row-click', item)"
        />
      </tbody>
    </table>

    <!-- 100개 이상: 가상 스크롤 (RecycleScroller) -->
    <RecycleScroller
      v-if="useVirtual && !loading && !error"
      class="w-full"
      :style="{ maxHeight: '600px' }"
      :items="sorted"
      :item-size="ROW_H"
      key-field="ticker"
    >
      <template #default="{ item }">
        <table class="w-full text-sm table-fixed">
          <tbody>
            <StockRow
              :item="item"
              :rank="item._rank"
              @click="emit('row-click', item)"
            />
          </tbody>
        </table>
      </template>
    </RecycleScroller>

  </div>
</template>

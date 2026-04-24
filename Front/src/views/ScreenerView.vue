<script setup>
import { ref, onMounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { useScreenerStore } from '@/stores/screener'
import { useThemeStore } from '@/stores/theme.js'
import FilterSidebar from '@/components/screener/FilterSidebar.vue'
import ScreenerTable from '@/components/screener/ScreenerTable.vue'

const store  = useScreenerStore()
const theme  = useThemeStore()
const filterSheetOpen = ref(false)

const fetchDebounced = useDebounceFn(() => store.fetchScreener(), 500)

function onFilterChange({ key, value }) {
  if (key === '_reload') { store.fetchScreener(); return }
  store.setFilter(key, value)
  fetchDebounced()
}

function onResetFinancial() { store.resetFinancialFilters(); store.fetchScreener() }
function onResetAll()       { store.resetAllFilters();       store.fetchScreener() }

onMounted(() => store.fetchScreener())
</script>

<template>
  <div class="max-w-[1400px] mx-auto px-4 py-4 md:py-6 pb-20 md:pb-6">

    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-4 md:mb-5">
      <div>
        <h1 class="text-lg md:text-xl font-semibold">스크리너</h1>
        <p class="text-sm mt-0.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
          ML 점수와 재무 지표를 조합해 종목을 필터링합니다
        </p>
      </div>
      <!-- 모바일: 필터 버튼 -->
      <button
        class="md:hidden text-sm border rounded-lg px-3 py-1.5 transition-colors"
        :class="theme.isDark ? 'border-[#2A2D3A] text-gray-400 hover:bg-white/10' : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
        @click="filterSheetOpen = true"
      >
        🔧 필터
      </button>
    </div>

    <!-- 데스크톱: 2컬럼 레이아웃 -->
    <div class="hidden md:grid grid-cols-[300px_1fr] gap-6 items-start">
      <FilterSidebar
        :filters="store.filters"
        @filter-change="onFilterChange"
        @reset-financial="onResetFinancial"
        @reset-all="onResetAll"
      />
      <ScreenerTable
        :items="store.items"
        :total="store.total"
        :loading="store.loading"
        :error="store.error"
        @reset-financial="onResetFinancial"
      />
    </div>

    <!-- 모바일: 테이블만 -->
    <div class="md:hidden">
      <ScreenerTable
        :items="store.items"
        :total="store.total"
        :loading="store.loading"
        :error="store.error"
        @reset-financial="onResetFinancial"
      />
    </div>

  </div>

  <!-- 모바일 필터 Bottom Sheet -->
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="filterSheetOpen" class="fixed inset-0 z-[70] md:hidden">
        <div class="absolute inset-0 bg-black/50" @click="filterSheetOpen = false" />
        <div
          class="absolute bottom-0 left-0 right-0 rounded-t-2xl max-h-[85vh] overflow-y-auto"
          :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-white'"
        >
          <div class="flex justify-center pt-3 pb-2">
            <div class="w-10 h-1 rounded-full bg-gray-300" />
          </div>
          <div class="flex items-center justify-between px-5 pb-3">
            <h3 class="font-semibold">필터</h3>
            <button @click="filterSheetOpen = false">✕</button>
          </div>
          <div class="px-2 pb-4">
            <FilterSidebar
              :filters="store.filters"
              @filter-change="onFilterChange"
              @reset-financial="onResetFinancial"
              @reset-all="onResetAll"
            />
          </div>
          <div class="px-4 pb-8">
            <button
              class="w-full py-3 rounded-xl font-medium text-sm transition-colors"
              :class="theme.isDark ? 'bg-white/10 text-white' : 'bg-gray-900 text-white'"
              @click="filterSheetOpen = false"
            >
              적용하기
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-enter-active, .sheet-leave-active { transition: opacity 0.25s; }
.sheet-enter-from, .sheet-leave-to { opacity: 0; }
</style>

<script setup>
import { ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { stocksApi } from '@/api/stocks'
import TierBadge from '@/components/common/TierBadge.vue'

const props = defineProps({
  selectedTickers: { type: Array,  default: () => [] },
  colorMap:        { type: Object, default: () => ({}) },
  stockNames:      { type: Object, default: () => ({}) }, // ticker → name mapping
})
const emit = defineEmits(['add-ticker', 'remove-ticker', 'search-done'])

const searchQuery         = ref('')
const searchDropdownItems = ref([])
const toast               = ref('')
let toastTimer            = null

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2000)
}

const doSearch = useDebounceFn(async () => {
  const q = searchQuery.value.trim()
  if (!q) { searchDropdownItems.value = []; return }
  try {
    const res = await stocksApi.searchStocks(q, 'latest', 10)
    searchDropdownItems.value = res.data.items ?? []
  } catch {
    searchDropdownItems.value = []
  }
}, 300)

function onInput() { doSearch() }

function selectTicker(item) {
  if (props.selectedTickers.includes(item.ticker)) {
    showToast('이미 추가된 종목입니다')
    return
  }
  if (props.selectedTickers.length >= 10) {
    showToast('최대 10개까지 비교 가능합니다')
    return
  }
  emit('add-ticker', item)
  searchQuery.value = ''
  searchDropdownItems.value = []
}

function closeDropdown() {
  setTimeout(() => { searchDropdownItems.value = [] }, 150)
}
</script>

<template>
  <div class="flex flex-col gap-3">

    <!-- 검색 인풋 -->
    <div class="relative">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="종목명 또는 티커 검색..."
        class="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-gray-400 transition-colors"
        @input="onInput"
        @blur="closeDropdown"
      />

      <!-- 드롭다운 -->
      <div
        v-if="searchDropdownItems.length"
        class="absolute left-0 right-0 top-full mt-1 bg-white border border-gray-100 rounded-xl shadow-lg z-50 max-h-64 overflow-y-auto"
      >
        <div
          v-for="item in searchDropdownItems"
          :key="item.ticker"
          class="flex items-center gap-2 px-3 py-2.5 hover:bg-gray-50 cursor-pointer"
          @mousedown.prevent="selectTicker(item)"
        >
          <span class="font-mono text-xs text-gray-400 w-16 shrink-0">{{ item.ticker }}</span>
          <span class="font-medium text-sm flex-1">{{ item.name }}</span>
          <span class="text-xs text-gray-400 mr-2">{{ item.sector }}</span>
          <TierBadge :tier="item.tier" />
        </div>
      </div>
    </div>

    <!-- 선택된 종목 태그 -->
    <div v-if="selectedTickers.length" class="flex flex-wrap gap-2">
      <div
        v-for="ticker in selectedTickers"
        :key="ticker"
        class="flex items-center gap-1.5 pl-2 pr-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-sm border-l-4"
        :style="{ borderLeftColor: colorMap[ticker] }"
      >
        <span class="font-medium text-gray-800">{{ stockNames[ticker] ?? ticker }}</span>
        <span class="font-mono text-xs text-gray-400">{{ ticker }}</span>
        <button class="text-gray-300 hover:text-gray-600 ml-1 transition-colors" @click="emit('remove-ticker', ticker)">
          ✕
        </button>
      </div>
    </div>

    <!-- 토스트 -->
    <Transition name="fade">
      <div
        v-if="toast"
        class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
      >
        {{ toast }}
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

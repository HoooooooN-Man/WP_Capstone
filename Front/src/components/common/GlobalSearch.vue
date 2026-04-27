<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useDebounceFn, useEventListener } from '@vueuse/core'
import { stocksApi } from '@/api/stocks'
import { useThemeStore } from '@/stores/theme.js'
import TierBadge from './TierBadge.vue'

const emit = defineEmits(['close'])
const router = useRouter()
const theme  = useThemeStore()

const query       = ref('')
const results     = ref([])
const activeIdx   = ref(0)
const loading     = ref(false)
const inputRef    = ref(null)

const RECENT_KEY  = 'global_search_recent'
const recentList  = ref(JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'))

const showResults = computed(() => query.value.trim().length > 0)

// ── 검색 ──────────────────────────────────────────────────────────────────────
const doSearch = useDebounceFn(async () => {
  const q = query.value.trim()
  if (!q) { results.value = []; return }
  loading.value = true
  try {
    const res = await stocksApi.searchStocks(q, 'latest', 10)
    results.value = res.data.items ?? []
    activeIdx.value = 0
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}, 200)

watch(query, doSearch)

// ── 최근 검색어 ───────────────────────────────────────────────────────────────
function saveRecent(item) {
  const list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
  const next = [item, ...list.filter(r => r.ticker !== item.ticker)].slice(0, 5)
  localStorage.setItem(RECENT_KEY, JSON.stringify(next))
  recentList.value = next
}

// ── 선택 ──────────────────────────────────────────────────────────────────────
function select(item) {
  saveRecent(item)
  router.push('/stocks/' + item.ticker)
  emit('close')
}

// ── 키보드 ────────────────────────────────────────────────────────────────────
const displayList = computed(() => showResults.value ? results.value : recentList.value)

useEventListener(document, 'keydown', (e) => {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIdx.value = (activeIdx.value + 1) % Math.max(displayList.value.length, 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIdx.value = (activeIdx.value - 1 + Math.max(displayList.value.length, 1)) % Math.max(displayList.value.length, 1)
  } else if (e.key === 'Enter') {
    const item = displayList.value[activeIdx.value]
    if (item) select(item)
  } else if (e.key === 'Escape') {
    emit('close')
  }
})

// 열릴 때 input focus
watch(() => true, () => {
  nextTick(() => inputRef.value?.focus())
}, { immediate: true })
</script>

<template>
  <Teleport to="body">
    <!-- 백드롭 -->
    <div
      class="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4"
      style="background: rgba(0,0,0,0.45)"
      @click.self="emit('close')"
    >
      <div
        class="w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden"
        :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white'"
      >
        <!-- 검색 입력 -->
        <div
          class="flex items-center gap-3 px-4 border-b"
          :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'"
        >
          <span class="text-gray-400 text-lg">🔍</span>
          <input
            ref="inputRef"
            v-model="query"
            type="text"
            placeholder="종목명 또는 티커 검색..."
            class="flex-1 py-4 text-sm bg-transparent focus:outline-none"
            :class="theme.isDark ? 'text-[#E4E6EF] placeholder-gray-600' : 'text-gray-900 placeholder-gray-400'"
            style="border: none !important; background: transparent !important;"
          />
          <span
            class="text-xs border rounded px-1.5 py-0.5 shrink-0"
            :class="theme.isDark ? 'border-[#2A2D3A] text-gray-500' : 'border-gray-200 text-gray-400'"
          >Esc</span>
        </div>

        <!-- 결과 / 최근 검색 -->
        <div class="max-h-[60vh] overflow-y-auto">

          <!-- 헤더 -->
          <p
            v-if="!showResults && recentList.length"
            class="px-4 pt-3 pb-1 text-xs font-medium"
            :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'"
          >
            최근 검색
          </p>
          <p
            v-else-if="showResults && !loading && !results.length"
            class="px-4 py-8 text-sm text-center"
            :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'"
          >
            검색 결과가 없습니다
          </p>

          <!-- 로딩 -->
          <div v-if="loading" class="flex justify-center py-6">
            <div class="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
          </div>

          <!-- 결과 목록 -->
          <div v-else>
            <div
              v-for="(item, idx) in displayList"
              :key="item.ticker"
              class="flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors"
              :class="[
                idx === activeIdx
                  ? (theme.isDark ? 'bg-white/10' : 'bg-gray-100')
                  : (theme.isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50')
              ]"
              @click="select(item)"
              @mouseover="activeIdx = idx"
            >
              <span
                class="font-mono text-xs w-16 shrink-0"
                :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'"
              >{{ item.ticker }}</span>
              <span
                class="font-medium text-sm flex-1"
                :class="theme.isDark ? 'text-[#E4E6EF]' : 'text-gray-900'"
              >{{ item.name }}</span>
              <span
                class="text-xs mr-2"
                :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'"
              >{{ item.sector }}</span>
              <TierBadge :tier="item.tier" />
            </div>
          </div>

          <!-- 빈 상태 -->
          <div v-if="!showResults && !recentList.length" class="px-4 py-8 text-center">
            <p class="text-sm" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
              종목명 또는 티커를 입력하세요
            </p>
            <p class="text-xs mt-1" :class="theme.isDark ? 'text-gray-600' : 'text-gray-300'">
              예: 삼성전자, 005930
            </p>
          </div>

        </div>

        <!-- 푸터 힌트 -->
        <div
          class="flex items-center gap-4 px-4 py-2.5 border-t text-xs"
          :class="theme.isDark ? 'border-[#2A2D3A] text-gray-600' : 'border-gray-100 text-gray-400'"
        >
          <span>↑↓ 이동</span>
          <span>Enter 선택</span>
          <span>Esc 닫기</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

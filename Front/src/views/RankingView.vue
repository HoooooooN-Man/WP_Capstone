<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme.js'
import { stocksApi } from '@/api/stocks'
import api from '@/api/axios.js'
import TierBadge from '@/components/common/TierBadge.vue'

const router = useRouter()
const theme  = useThemeStore()

const activeTab  = ref('ai')   // 'ai' | 'community' | 'rising'
const loading    = ref(false)
const aiList     = ref([])
const communityList = ref([])
const risingList = ref([])

// ── 데이터 로드 ───────────────────────────────────────────────────────────────
async function fetchAiRanking() {
  const { data } = await stocksApi.getRecommendations({ top_k: 20 })
  aiList.value = (data.items ?? []).slice(0, 20)
}

async function fetchCommunity() {
  try {
    const { data } = await api.get('/board/popular?limit=20')
    communityList.value = data.items ?? data ?? []
  } catch {
    communityList.value = []
  }
}

async function fetchRising() {
  try {
    const { data } = await api.get('/stocks/rising?limit=20')
    risingList.value = data.items ?? []
  } catch {
    // API 미구현 시 AI 랭킹에서 상위 종목으로 대체
    risingList.value = aiList.value.slice(0, 20)
  }
}

async function loadAll() {
  loading.value = true
  try {
    await fetchAiRanking()
    await Promise.allSettled([fetchCommunity(), fetchRising()])
  } finally {
    loading.value = false
  }
}

const currentList = computed(() => {
  if (activeTab.value === 'ai')        return aiList.value
  if (activeTab.value === 'community') return communityList.value
  return risingList.value
})

// 탭 메타
const tabs = [
  { id: 'ai',        label: 'AI 추천 랭킹',   icon: '🤖', desc: '오늘 ML 점수 Top 20' },
  { id: 'community', label: '커뮤니티 인기',  icon: '🔥', desc: '게시판 좋아요 순 Top 20' },
  { id: 'rising',    label: '급상승 종목',    icon: '🚀', desc: '전일 대비 점수 상승폭 Top 20' },
]

// 등수 뱃지 색상
function rankStyle(i) {
  if (i === 0) return 'text-yellow-500 font-bold text-lg'
  if (i === 1) return 'text-gray-400 font-bold text-lg'
  if (i === 2) return 'text-amber-600 font-bold text-lg'
  return 'text-gray-400 font-medium text-sm'
}

function getScore(item) {
  return item.score ?? item.avg_score ?? item.likes ?? 0
}
function getScoreLabel() {
  if (activeTab.value === 'ai')        return 'ML 점수'
  if (activeTab.value === 'community') return '좋아요'
  return '점수 상승'
}

onMounted(loadAll)
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-4 md:py-6 pb-20 md:pb-6">

    <!-- 헤더 -->
    <div class="mb-6">
      <h1 class="text-xl font-semibold">종목 랭킹</h1>
      <p class="text-sm mt-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
        AI 분석, 커뮤니티 인기, 급상승 종목을 한눈에
      </p>
    </div>

    <!-- 탭 -->
    <div
      class="flex rounded-xl p-1 mb-6 gap-1"
      :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-gray-100'"
    >
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="flex-1 flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-1.5 py-2.5 px-2 rounded-lg text-sm font-medium transition-all"
        :class="activeTab === tab.id
          ? (theme.isDark ? 'bg-[#0F1117] text-white shadow-sm' : 'bg-white text-gray-900 shadow-sm')
          : (theme.isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700')"
        @click="activeTab = tab.id"
      >
        <span>{{ tab.icon }}</span>
        <span class="text-xs sm:text-sm">{{ tab.label }}</span>
      </button>
    </div>

    <!-- 탭 설명 -->
    <p class="text-xs mb-4" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">
      {{ tabs.find(t => t.id === activeTab)?.desc }}
    </p>

    <!-- 로딩 -->
    <div v-if="loading" class="flex justify-center py-20">
      <div class="w-8 h-8 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
    </div>

    <!-- 빈 상태 -->
    <div
      v-else-if="!currentList.length"
      class="text-center py-16 rounded-2xl"
      :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-gray-50'"
    >
      <p class="text-sm" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
        {{ activeTab === 'community' ? '커뮤니티 API 연결 후 표시됩니다' : '데이터가 없습니다' }}
      </p>
    </div>

    <!-- 랭킹 리스트 -->
    <div
      v-else
      class="rounded-2xl overflow-hidden"
      :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
    >
      <div
        v-for="(item, idx) in currentList"
        :key="item.ticker ?? item.id ?? idx"
        class="flex items-center gap-4 px-5 py-4 cursor-pointer transition-colors"
        :class="[
          idx > 0 ? (theme.isDark ? 'border-t border-[#2A2D3A]' : 'border-t border-gray-50') : '',
          theme.isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'
        ]"
        @click="item.ticker && router.push('/stocks/' + item.ticker)"
      >
        <!-- 등수 -->
        <span class="w-7 text-center shrink-0" :class="rankStyle(idx)">
          {{ idx < 3 ? ['🥇','🥈','🥉'][idx] : idx + 1 }}
        </span>

        <!-- 종목 정보 -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-semibold text-sm truncate">{{ item.name ?? item.title ?? item.ticker }}</span>
            <TierBadge v-if="item.tier" :tier="item.tier" />
          </div>
          <div class="flex items-center gap-2 mt-0.5">
            <span
              class="font-mono text-xs"
              :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'"
            >{{ item.ticker }}</span>
            <span
              class="text-xs"
              :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'"
            >{{ item.sector }}</span>
          </div>
        </div>

        <!-- 점수 -->
        <div class="text-right shrink-0">
          <p class="font-bold text-sm">
            {{ typeof getScore(item) === 'number' ? getScore(item).toFixed?.(1) ?? getScore(item) : getScore(item) }}
          </p>
          <p class="text-xs mt-0.5" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">
            {{ getScoreLabel() }}
          </p>
        </div>

        <!-- 점수 바 (AI 랭킹만) -->
        <div v-if="activeTab === 'ai'" class="w-16 shrink-0">
          <div class="h-1.5 rounded-full overflow-hidden" :class="theme.isDark ? 'bg-[#0F1117]' : 'bg-gray-100'">
            <div
              class="h-full rounded-full transition-all"
              style="background: linear-gradient(90deg, #5B6DFF, #F03E4C)"
              :style="{ width: `${Math.min(100, item.score ?? 0)}%` }"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 새로고침 -->
    <div class="mt-4 text-center">
      <button
        class="text-sm transition-colors"
        :class="theme.isDark ? 'text-gray-600 hover:text-gray-400' : 'text-gray-400 hover:text-gray-600'"
        @click="loadAll"
      >
        ↻ 새로고침
      </button>
    </div>

  </div>
</template>

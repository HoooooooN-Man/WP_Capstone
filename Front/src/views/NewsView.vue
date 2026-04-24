<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { useThemeStore } from '@/stores/theme.js'
import api from '@/api/axios.js'

const route  = useRoute()
const router = useRouter()
const theme  = useThemeStore()

const activeFilter = ref('all')   // 'all' | 'positive' | 'neutral' | 'negative'
const tickerFilter = ref('')
const loading = ref(false)
const news    = ref([])
const total   = ref(0)
const page    = ref(1)
const PER     = 20

// 필터 탭
const sentimentTabs = [
  { id: 'all',      label: '전체',  icon: '📰', color: '' },
  { id: 'positive', label: '긍정',  icon: '✅', color: 'text-green-600' },
  { id: 'neutral',  label: '중립',  icon: '➖', color: 'text-gray-500' },
  { id: 'negative', label: '부정',  icon: '⚠️', color: 'text-red-500' },
]

// ── fetch ──────────────────────────────────────────────────────────────────────
async function fetchNews(reset = false) {
  if (reset) { page.value = 1; news.value = [] }
  loading.value = true
  try {
    const params = {
      limit: PER,
      offset: (page.value - 1) * PER,
    }
    if (activeFilter.value !== 'all') params.sentiment = activeFilter.value
    if (tickerFilter.value.trim())    params.ticker    = tickerFilter.value.trim().toUpperCase()

    const { data } = await api.get('/news/feed', { params })
    const items = data.items ?? data ?? []
    total.value = data.total ?? items.length
    if (reset) news.value = items
    else       news.value.push(...items)
  } catch {
    // 모의 데이터
    if (reset) news.value = mockNews()
    total.value = mockNews().length
  } finally {
    loading.value = false
  }
}

function mockNews() {
  const now = new Date()
  const sentiments = ['positive', 'neutral', 'negative']
  const companies = [
    { ticker: '005930', name: '삼성전자' },
    { ticker: '000660', name: 'SK하이닉스' },
    { ticker: '035420', name: 'NAVER' },
    { ticker: '005380', name: '현대차' },
    { ticker: '051910', name: 'LG화학' },
  ]
  return Array.from({ length: 20 }, (_, i) => {
    const c = companies[i % companies.length]
    const s = sentiments[i % 3]
    return {
      id: i + 1,
      ticker: c.ticker,
      company_name: c.name,
      title: `${c.name} 관련 주요 뉴스 ${i + 1}`,
      source: ['한국경제', '매일경제', '조선비즈'][i % 3],
      published_at: new Date(now - i * 3600000).toISOString(),
      sentiment_label: s,
      sentiment_score: s === 'positive' ? 0.85 - i * 0.01 : s === 'negative' ? 0.7 - i * 0.01 : 0.6,
      url: '#',
    }
  })
}

// ── 감성 배지 ──────────────────────────────────────────────────────────────────
function sentimentBadge(s) {
  const map = {
    positive: { label: '긍정', cls: theme.isDark ? 'bg-green-900/50 text-green-400' : 'bg-green-50 text-green-700' },
    neutral:  { label: '중립', cls: theme.isDark ? 'bg-gray-800 text-gray-400'      : 'bg-gray-100 text-gray-500' },
    negative: { label: '부정', cls: theme.isDark ? 'bg-red-900/50 text-red-400'     : 'bg-red-50 text-red-600' },
  }
  return map[s] ?? map.neutral
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - d) / 60000)
  if (diff < 1)   return '방금 전'
  if (diff < 60)  return `${diff}분 전`
  if (diff < 1440) return `${Math.floor(diff / 60)}시간 전`
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}

// ── 더 보기 ────────────────────────────────────────────────────────────────────
const hasMore = computed(() => news.value.length < total.value)
function loadMore() { page.value++; fetchNews() }

// ── 검색 디바운스 ──────────────────────────────────────────────────────────────
const debouncedFetch = useDebounceFn(() => fetchNews(true), 400)
watch(tickerFilter, debouncedFetch)
watch(activeFilter, () => fetchNews(true))

// URL 동기화
watch(activeFilter, (v) => router.replace({ query: { ...route.query, sentiment: v === 'all' ? undefined : v } }))

onMounted(() => {
  if (route.query.sentiment) activeFilter.value = route.query.sentiment
  fetchNews(true)
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-4 md:py-6 pb-20 md:pb-6">

    <!-- 헤더 -->
    <div class="mb-5">
      <h1 class="text-xl font-semibold">뉴스 감성 피드</h1>
      <p class="text-sm mt-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
        FinBERT 감성 분석 결과 기반 실시간 종목 뉴스
      </p>
    </div>

    <!-- 티커 검색 -->
    <div class="mb-4">
      <input
        v-model="tickerFilter"
        type="text"
        placeholder="종목 티커 검색 (예: 005930)"
        class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
        :class="theme.isDark
          ? 'bg-[#1A1D27] border-[#2A2D3A] text-[#E4E6EF] placeholder-gray-600 focus:border-gray-500'
          : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-gray-400'"
      />
    </div>

    <!-- 감성 탭 -->
    <div class="flex gap-2 mb-5">
      <button
        v-for="tab in sentimentTabs"
        :key="tab.id"
        class="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium transition-colors"
        :class="activeFilter === tab.id
          ? (theme.isDark ? 'bg-white/15 text-white' : 'bg-gray-900 text-white')
          : (theme.isDark ? 'bg-[#1A1D27] text-gray-500 hover:text-gray-300' : 'bg-gray-100 text-gray-500 hover:text-gray-700')"
        @click="activeFilter = tab.id"
      >
        <span>{{ tab.icon }}</span>
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <!-- 로딩 -->
    <div v-if="loading && !news.length" class="flex justify-center py-20">
      <div class="w-8 h-8 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
    </div>

    <!-- 빈 상태 -->
    <div
      v-else-if="!loading && !news.length"
      class="text-center py-16 rounded-2xl"
      :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-gray-50'"
    >
      <p class="text-2xl mb-2">📭</p>
      <p class="text-sm" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">뉴스가 없습니다</p>
    </div>

    <!-- 뉴스 목록 -->
    <div v-else class="space-y-3">
      <a
        v-for="item in news"
        :key="item.id"
        :href="item.url !== '#' ? item.url : undefined"
        :target="item.url !== '#' ? '_blank' : undefined"
        class="block rounded-xl p-4 border transition-colors"
        :class="theme.isDark
          ? 'bg-[#1A1D27] border-[#2A2D3A] hover:border-gray-600'
          : 'bg-white border-gray-100 hover:border-gray-200'"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <!-- 회사명 + 배지 -->
            <div class="flex items-center gap-2 mb-1.5 flex-wrap">
              <button
                class="text-xs font-medium px-2 py-0.5 rounded-md transition-colors"
                :class="theme.isDark ? 'bg-white/10 text-gray-300 hover:bg-white/20' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
                @click.prevent="tickerFilter = item.ticker"
              >
                {{ item.ticker }}
              </button>
              <span class="text-xs font-medium" :class="theme.isDark ? 'text-gray-400' : 'text-gray-600'">
                {{ item.company_name }}
              </span>
              <span
                class="text-xs px-2 py-0.5 rounded-full font-medium"
                :class="sentimentBadge(item.sentiment_label).cls"
              >
                {{ sentimentBadge(item.sentiment_label).label }}
              </span>
            </div>
            <!-- 제목 -->
            <p class="text-sm font-medium leading-snug line-clamp-2">{{ item.title }}</p>
          </div>
        </div>

        <!-- 메타 정보 -->
        <div class="flex items-center gap-3 mt-2.5">
          <span class="text-xs" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">
            {{ item.source }}
          </span>
          <span class="text-xs" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">
            {{ formatDate(item.published_at) }}
          </span>
          <span v-if="item.sentiment_score" class="text-xs ml-auto" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">
            신뢰도 {{ (item.sentiment_score * 100).toFixed(0) }}%
          </span>
        </div>
      </a>
    </div>

    <!-- 더 보기 -->
    <div v-if="hasMore" class="mt-6 text-center">
      <button
        class="px-6 py-2.5 rounded-xl text-sm font-medium transition-colors"
        :class="theme.isDark ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
        :disabled="loading"
        @click="loadMore"
      >
        <span v-if="loading">로딩 중...</span>
        <span v-else>더 보기 ({{ total - news.length }}개 남음)</span>
      </button>
    </div>

  </div>
</template>

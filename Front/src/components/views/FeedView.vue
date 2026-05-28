<template>
  <div class="w-full h-full bg-gradient-to-br from-[#1a1f1a] to-[#0e120e] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden border border-white/10 text-white">

    <!-- 헤더 -->
    <div class="px-5 pt-4 pb-3 border-b border-white/10 flex-shrink-0 flex items-center justify-between">
      <div>
        <p class="text-[13px] text-white/40 uppercase tracking-widest mb-0.5">AI Market Intelligence</p>
        <h2 class="text-2xl font-black tracking-tighter uppercase">Latest Feed</h2>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="!loading" class="text-[13px] text-white/30">{{ recDate }}</span>
        <div class="px-2.5 py-1 bg-green-500/20 rounded-full border border-green-500/40">
          <span class="text-[14px] text-green-300 font-bold uppercase tracking-wider">LIVE</span>
        </div>
      </div>
    </div>

    <!-- 로딩 -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <svg class="animate-spin w-6 h-6 text-[#c9a227]/50" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"
                stroke-dasharray="60" stroke-dashoffset="20" stroke-linecap="round"/>
      </svg>
    </div>

    <!-- 피드 리스트 -->
    <div v-else class="flex-1 overflow-y-auto px-3 py-3 space-y-2">
      <div
        v-for="item in feeds" :key="item.id"
        class="p-3 rounded-xl bg-white/5 border border-white/8 hover:bg-white/8 transition-colors"
      >
        <div class="flex items-start justify-between gap-3 mb-1.5">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="badge" :class="tierBadgeColor(item.tier)">{{ item.tier }}-TIER</span>
            <span class="badge" :class="categoryColor(item.category)">{{ item.category }}</span>
            <span v-if="item.ticker" class="text-[13px] text-white/30 font-mono">{{ item.ticker }}</span>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-[13px] font-bold text-[#c9a227]">{{ item.score }}점</span>
            <span class="text-[13px] text-white/25">{{ item.time }}</span>
          </div>
        </div>
        <p class="text-[14px] font-bold leading-snug">{{ item.title }}</p>
        <p class="text-[14px] text-white/45 mt-0.5 leading-snug">{{ item.body }}</p>
      </div>

      <div v-if="!feeds.length" class="flex items-center justify-center py-12 text-white/25 text-sm">
        데이터를 불러오는 중입니다
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { stocksApi } from '@/api/stocks.js'

const loading = ref(true)
const recDate = ref('')
const rawItems = ref([])

// 추천 데이터를 피드 형태로 변환
const feeds = computed(() => {
  return rawItems.value.map((item, idx) => {
    const tier    = item.tier ?? 'C'
    const sector  = item.sector ?? 'Market'
    const score   = Math.round(item.score ?? 0)
    const name    = item.name ?? item.ticker

    const CATEGORIES = {
      A: ['TOP PICK', 'HOT', 'STRONG BUY'],
      B: ['WATCH', 'BUY', 'TRENDING'],
      C: ['NEUTRAL', 'HOLD', 'MARKET'],
      D: ['CAUTION', 'REVIEW', 'WEAK'],
    }
    const cats = CATEGORIES[tier] ?? CATEGORIES.C
    const category = cats[idx % cats.length]

    const TITLES = {
      A: `${name} — AI 최고점 ${score}점 달성, 강력 추천`,
      B: `${name} — 상위 티어 진입, 점수 ${score}점`,
      C: `${name} — ${sector} 섹터 모니터링 중`,
      D: `${name} — 주의 구간, 점수 ${score}점`,
    }

    return {
      id:       item.ticker + idx,
      tier,
      category,
      ticker:   item.ticker,
      score,
      time:     recDate.value || '—',
      title:    TITLES[tier] ?? TITLES.C,
      body:     `섹터: ${sector} · 앙상블 확률: ${((item.prob_ensemble ?? score / 100) * 100).toFixed(1)}% · 전체 ${item.total_in_date ?? '—'}종목 중 ${item.rank_in_date ?? idx + 1}위`,
    }
  })
})

async function load() {
  loading.value = true
  try {
    const { data } = await stocksApi.getRecommendations({ top_k: 30 })
    rawItems.value = data.items ?? []
    recDate.value  = data.date  ?? ''
  } catch {
    rawItems.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)

const tierBadgeColor = (tier) => ({
  A: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/35',
  B: 'bg-blue-500/20 text-blue-300 border border-blue-500/35',
  C: 'bg-amber-500/20 text-amber-300 border border-amber-500/35',
  D: 'bg-red-500/20 text-red-300 border border-red-500/35',
}[tier] ?? 'bg-white/10 text-white/50 border border-white/20')

const categoryColor = (cat) => {
  if (['TOP PICK', 'STRONG BUY', 'HOT'].includes(cat)) return 'badge-gold'
  if (['BUY', 'WATCH', 'TRENDING'].includes(cat))       return 'badge-green'
  if (['NEUTRAL', 'HOLD', 'MARKET'].includes(cat))      return 'bg-blue-500/20 text-blue-300 border border-blue-500/35'
  return 'bg-red-500/15 text-red-300 border border-red-500/30'
}
</script>

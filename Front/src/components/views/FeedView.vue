<template>
  <div class="w-full h-full rounded-[2rem] flex flex-col overflow-hidden border border-black/20"
       style="background: #f0e8d0; color: #1a1209; font-family: Georgia, 'Times New Roman', serif;">

    <!-- 마스트헤드 -->
    <div class="flex-shrink-0 px-5 pt-3 pb-0" style="border-bottom: 3px double #1a1209;">
      <div class="flex items-center justify-between mb-1" style="font-family: sans-serif;">
        <span class="text-[10px] tracking-widest uppercase" style="color: #888;">AI Market Intelligence</span>
        <span class="text-[10px] tracking-widest" style="color: #888;">{{ recDate || '' }}</span>
      </div>
      <h1 class="text-center font-black py-1.5 tracking-tight"
          style="font-size: 26px; letter-spacing: -0.02em; border-top: 2px solid #1a1209; border-bottom: 1px solid #1a1209;">
        MARKET GAZETTE
      </h1>
      <div class="flex items-center justify-between py-1.5" style="font-family: sans-serif; border-bottom: 2px solid #1a1209;">
        <span class="text-[10px]" style="color: #666;">AI 추천 종목 뉴스레터 · Wallet Protector</span>
        <div v-if="!loading" class="flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-green-600 animate-pulse inline-block"></span>
          <span class="text-[10px] font-bold uppercase tracking-widest" style="color: #2d6a2d; font-family: sans-serif;">LIVE</span>
        </div>
        <span v-else class="text-[10px] italic" style="color: #888; font-family: sans-serif;">취재 중...</span>
      </div>
    </div>

    <!-- 로딩 -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <p class="text-[14px] italic" style="color: #888;">시황을 분석 중입니다...</p>
    </div>

    <!-- 기사 리스트 -->
    <div v-else class="flex-1 overflow-y-auto">

      <!-- 헤드라인 (첫 번째 A티어) -->
      <div v-if="topArticle" class="px-5 py-3" style="border-bottom: 2px solid #c8b89a; background: #ece3c5;">
        <div class="flex items-center gap-2 mb-1.5" style="font-family: sans-serif;">
          <span class="text-[9px] font-black px-1.5 py-0.5 uppercase tracking-widest text-white"
                :style="{ background: tierColor(topArticle.tier) }">
            {{ topArticle.tier }}-TIER
          </span>
          <span class="text-[10px] font-black uppercase tracking-wider" style="color: #9a6e10; font-family: sans-serif;">
            {{ topArticle.category }}
          </span>
          <span class="ml-auto text-[12px] font-black" style="color: #9a6e10; font-family: sans-serif;">
            {{ topArticle.score }}점
          </span>
        </div>
        <h2 class="font-black leading-tight mb-2" style="font-size: 18px;">{{ topArticle.title }}</h2>
        <p class="leading-relaxed" style="font-size: 12px; color: #5a4020;">{{ topArticle.body }}</p>
        <p class="mt-1.5 text-[10px] font-mono" style="color: #aaa; font-family: sans-serif;">{{ topArticle.ticker }}</p>
      </div>

      <!-- 나머지 기사 -->
      <div
        v-for="(item, idx) in restArticles" :key="item.id"
        class="px-5 py-2.5"
        :style="idx < restArticles.length - 1 ? 'border-bottom: 1px solid #d4c8a8;' : ''"
      >
        <div class="flex items-start gap-3">
          <!-- 티어 컬럼 -->
          <div class="flex-shrink-0 pt-0.5">
            <span class="text-[9px] font-black px-1 py-0.5 uppercase tracking-widest text-white"
                  :style="{ background: tierColor(item.tier) }">
              {{ item.tier }}
            </span>
          </div>
          <!-- 기사 본문 -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 mb-0.5" style="font-family: sans-serif;">
              <span class="text-[10px] font-bold uppercase tracking-wider" style="color: #888;">{{ item.category }}</span>
              <span class="text-[10px] font-mono" style="color: #bbb;">{{ item.ticker }}</span>
              <span class="ml-auto text-[11px] font-black flex-shrink-0" style="color: #9a6e10; font-family: sans-serif;">{{ item.score }}점</span>
            </div>
            <h3 class="font-black leading-snug mb-0.5" style="font-size: 13px;">{{ item.title }}</h3>
            <p class="leading-relaxed line-clamp-2" style="font-size: 11px; color: #6a5030;">{{ item.body }}</p>
          </div>
        </div>
      </div>

      <div v-if="!feeds.length" class="flex items-center justify-center py-12">
        <p class="text-[13px] italic" style="color: #aaa">기사를 불러오는 중입니다...</p>
      </div>

      <!-- 푸터 -->
      <div class="px-5 py-3 text-center" style="border-top: 2px double #1a1209; font-family: sans-serif;">
        <p class="text-[9px] uppercase tracking-widest" style="color: #aaa;">
          본 뉴스레터는 AI 분석 기반으로 투자 권유가 아닙니다
        </p>
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

const topArticle  = computed(() => feeds.value.find(f => f.tier === 'A') ?? feeds.value[0] ?? null)
const restArticles = computed(() => feeds.value.filter(f => f !== topArticle.value))

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

const tierColor = (tier) => ({
  A: '#065f46',
  B: '#1e3a8a',
  C: '#92400e',
  D: '#991b1b',
}[tier] ?? '#374151')
</script>

<template>
  <div class="w-full h-full overflow-hidden relative"
       style="background:#ccc8c0; color:#1a1209;">
    <!-- 신문 줄 질감 오버레이 -->
    <div class="absolute inset-0 pointer-events-none"
         style="background-image:repeating-linear-gradient(0deg,transparent,transparent 22px,rgba(0,0,0,0.025) 22px,rgba(0,0,0,0.025) 23px);"></div>

    <div class="absolute inset-0 overflow-y-auto" style="font-family:Georgia,'Times New Roman',serif;">

      <!-- ═══ 마스트헤드 ═══ -->
      <div class="px-5 pt-3 flex-shrink-0" style="border-bottom:3px double #1a1209;">
        <!-- 상단 얇은 정보 바 -->
        <div class="flex items-center justify-between pb-1 mb-0.5" style="border-bottom:1px solid rgba(0,0,0,0.2); font-family:sans-serif;">
          <span class="text-[8px] uppercase tracking-widest" style="color:#777;">AI Financial Intelligence</span>
          <div v-if="!recLoading" class="flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-green-700 animate-pulse inline-block"></span>
            <span class="text-[8px] font-bold uppercase tracking-widest" style="color:#2d5a1b;">LIVE</span>
          </div>
        </div>
        <!-- 메인 마스트헤드: 날짜(좌) | 제목(중) | 스코어(우) -->
        <div class="grid py-1.5" style="grid-template-columns:1fr auto 1fr; border-top:2px solid #1a1209; border-bottom:1px solid #1a1209; align-items:center; gap:8px;">
          <!-- 왼쪽: 날짜/에디션 -->
          <div style="font-family:sans-serif;">
            <p class="text-[8px] uppercase tracking-wide" style="color:#888;">Daily Edition</p>
            <p class="text-[11px] font-bold" style="color:#333;">{{ todayStr }}</p>
            <p class="text-[8px]" style="color:#aaa;">Vol. {{ todayVol }}</p>
          </div>
          <!-- 중앙: 제목 -->
          <h1 class="text-center font-black tracking-tight" style="font-size:26px; letter-spacing:-0.02em; font-family:Georgia,serif; white-space:nowrap;">
            MARKET GAZETTE
          </h1>
          <!-- 오른쪽: AI 마켓 스코어 -->
          <div class="text-right" style="font-family:sans-serif;">
            <p class="text-[8px] uppercase tracking-wide" style="color:#888;">AI Market Score</p>
            <p v-if="recLoading" class="text-[11px] italic" style="color:#aaa;">—</p>
            <template v-else>
              <p class="text-[18px] font-black leading-none" style="color:#1a1209;">{{ marketScore }}</p>
              <p class="text-[9px] font-bold" style="color:#4a7a10;">{{ marketLabel }}</p>
            </template>
          </div>
        </div>
        <!-- 하단 부제 -->
        <div class="flex items-center justify-between pt-1 pb-1.5" style="border-bottom:2px solid #1a1209; font-family:sans-serif;">
          <span class="text-[8px]" style="color:#777;">AI Score · 지수 · 추천 종목 · 뉴스 감성 랭킹</span>
          <span class="text-[8px]" style="color:#999;">{{ recDate || '' }}</span>
        </div>
      </div>

      <!-- ═══ AI 마켓 스코어 + 지수 ═══ -->
      <div class="px-5 py-3" style="border-bottom:2px solid rgba(0,0,0,0.2);">
        <div class="flex items-baseline gap-2 mb-3">
          <span class="text-[10px] font-black uppercase tracking-widest" style="color:#666;font-family:sans-serif;">AI Market Score</span>
          <span v-if="recLoading" class="text-[11px] italic" style="color:#aaa;">분석 중...</span>
          <template v-else>
            <span class="text-[30px] font-black leading-none">{{ marketScore }}</span>
            <span class="text-[13px]" style="color:#666;">/100</span>
            <span class="text-[12px] font-bold" style="color:#4a7a10;">{{ marketLabel }}</span>
          </template>
        </div>
        <div class="grid grid-cols-5 gap-2">
          <div v-for="idx in INDICES" :key="idx.name">
            <p class="text-[9px] font-bold uppercase tracking-wide" style="color:#888;font-family:sans-serif;">{{ idx.name }}</p>
            <p class="text-[14px] font-black">{{ idx.value }}</p>
            <p class="text-[10px] font-bold" :class="idx.up ? 'text-green-700' : 'text-red-600'">
              {{ idx.up ? '▲' : '▼' }} {{ idx.change }}
            </p>
          </div>
        </div>
      </div>

      <!-- ═══ AI 추천 종목 ═══ -->
      <div class="px-5 py-3" style="border-bottom:2px solid #1a1209;">
        <h2 class="text-[10px] font-black uppercase tracking-widest mb-2 pb-1"
            style="font-family:sans-serif; border-bottom:1px solid rgba(0,0,0,0.15);">
          ■ AI 추천 종목 Top 5
        </h2>
        <div v-if="recLoading" class="flex justify-center py-3">
          <span class="text-[12px] italic" style="color:#aaa;">집계 중...</span>
        </div>
        <div v-else>
          <div v-for="(stock, i) in topStocks" :key="stock.ticker"
               class="flex items-center gap-2 py-1.5"
               :style="i < topStocks.length-1 ? 'border-bottom:1px solid rgba(0,0,0,0.1)' : ''">
            <span class="font-black w-4 text-center leading-none" style="font-size:16px; color:#ccc;">{{ i+1 }}</span>
            <span class="font-bold text-[13px] flex-1 leading-tight">{{ stock.name ?? stock.ticker }}</span>
            <span class="text-[10px] font-mono" style="color:#888;">{{ stock.ticker }}</span>
            <span class="text-[12px] font-black" style="color:#8B6914;">{{ Math.round(stock.score) }}</span>
            <span class="text-[9px] px-1 py-0.5 font-black" style="background:#1a1209;color:#ccc8c0;font-family:sans-serif;">{{ stock.tier }}</span>
          </div>
          <div v-if="!topStocks.length" class="text-center py-2 text-[12px] italic" style="color:#aaa;">
            추천 데이터를 불러오는 중입니다
          </div>
        </div>
      </div>

      <!-- ═══ 뉴스 감성 랭킹 ═══ -->
      <div>
        <!-- 섹션 헤더 + 필터 -->
        <div class="px-5 pt-3 pb-1.5" style="border-bottom:1px solid rgba(0,0,0,0.15);">
          <h2 class="text-[10px] font-black uppercase tracking-widest mb-2"
              style="font-family:sans-serif;">■ 뉴스 감성 랭킹</h2>
          <div class="flex gap-0">
            <button v-for="f in ['전체','긍정','중립','부정']" :key="f"
                    @click="rankingFilter = f"
                    class="flex-1 py-0.5 text-[10px] font-bold transition-all"
                    :style="rankingFilter === f ? 'background:#1a1209;color:#ccc8c0;' : 'color:#888;'"
                    style="font-family:sans-serif;">
              {{ f }}
            </button>
          </div>
        </div>

        <!-- 로딩 -->
        <div v-if="rankingLoading" class="flex justify-center py-8">
          <span class="text-[13px] italic" style="color:#888;">집계 중...</span>
        </div>
        <!-- 오류 -->
        <div v-else-if="rankingError" class="flex flex-col items-center justify-center py-8 gap-1 text-center px-4">
          <span class="text-[13px] font-bold">데이터 준비 중</span>
          <span class="text-[11px] italic" style="color:#888;">뉴스 DB가 아직 생성되지 않았습니다</span>
        </div>
        <!-- 랭킹 아이템 -->
        <template v-else>
          <div v-for="(item, idx) in displayRankings" :key="item.news_id"
               class="flex items-start gap-3 px-5 py-2.5 cursor-pointer hover:bg-black/5"
               :style="idx < displayRankings.length-1 ? 'border-bottom:1px solid rgba(0,0,0,0.1)' : ''"
               :class="!filteredRankingNews.length ? 'opacity-60' : ''"
               @click="openUrl(item.origin_url || item.google_url)">
            <span class="flex-shrink-0 font-black text-center leading-none pt-0.5"
                  style="font-size:17px; min-width:20px; font-family:Georgia,serif;"
                  :style="{ color: item.rank <= 3 ? '#8B6914' : '#bbb' }">
              {{ item.rank }}
            </span>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5 mb-0.5" style="font-family:sans-serif;">
                <span class="text-[9px] font-bold uppercase tracking-wide px-1 py-0.5 text-white flex-shrink-0"
                      :style="{ background: sentimentColor(item.sentiment_label) }">
                  {{ sentimentKo(item.sentiment_label) }}
                </span>
                <span class="text-[9px] font-mono truncate" style="color:#888;">{{ item.provider }}</span>
                <span class="ml-auto text-[9px] font-bold flex-shrink-0" style="color:#8B6914;font-family:sans-serif;">
                  {{ (item.ranking_score ?? 0).toFixed(1) }}pt
                </span>
              </div>
              <p class="font-bold leading-snug" style="font-size:13px;">{{ item.title }}</p>
              <p class="text-[10px] mt-0.5" style="color:#999;font-family:sans-serif;">{{ formatDate(item.published_at) }}</p>
            </div>
          </div>
        </template>

        <!-- 푸터 -->
        <div class="px-5 py-3 text-center" style="border-top:2px double #1a1209;font-family:sans-serif;">
          <p class="text-[9px] uppercase tracking-widest" style="color:#aaa;">본 뉴스레터는 AI 분석 기반으로 투자 권유가 아닙니다</p>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useNewsRankings } from '@/composables/useStockQuery.js'
import { stocksApi } from '@/api/stocks.js'

// ── 랭킹 데이터 ────────────────────────────────────────────────
const rankingFilter = ref('전체')
const rankingParams = ref({ limit: 30 })
const { data: rankingData, isLoading: rankingLoading, isError: rankingError } = useNewsRankings(rankingParams)

const rankingList = computed(() => rankingData.value?.items ?? [])

const filteredRankingNews = computed(() =>
  rankingFilter.value === '전체'
    ? rankingList.value
    : rankingList.value.filter(n => sentimentKo(n.sentiment_label) === rankingFilter.value)
)

const displayRankings = computed(() =>
  filteredRankingNews.value.length ? filteredRankingNews.value : MOCK_RANKINGS
)

// ── 날짜 표기 ──────────────────────────────────────────────────
const now = new Date()
const todayStr = now.toLocaleDateString('ko-KR', { year:'numeric', month:'long', day:'numeric' })
const todayVol = Math.floor((now - new Date('2024-01-01')) / (1000 * 60 * 60 * 24))

// ── 마켓 데이터 ────────────────────────────────────────────────
const recommendations = ref([])
const recLoading      = ref(true)
const recDate         = ref('')

const INDICES = [
  { name: 'KOSPI',   value: '2,504', change: '+12.3', up: true  },
  { name: 'KOSDAQ',  value: '721',   change: '-3.2',  up: false },
  { name: 'USD/KRW', value: '1,365', change: '+2.5',  up: true  },
  { name: 'KP200',   value: '332',   change: '+1.8',  up: true  },
  { name: 'WTI',     value: '78.6',  change: '-0.3',  up: false },
]

const marketScore = computed(() => {
  if (!recommendations.value.length) return 0
  const top = recommendations.value.slice(0, 50)
  return Math.round(top.reduce((s, r) => s + (r.score ?? 0), 0) / top.length)
})

const marketLabel = computed(() => {
  const s = marketScore.value
  if (s >= 80) return '강세 🔥'
  if (s >= 65) return '양호 📈'
  if (s >= 50) return '보통 ➡️'
  if (s >= 35) return '약세 📉'
  return '침체 ❄️'
})

const topStocks = computed(() => recommendations.value.slice(0, 5))

onMounted(async () => {
  try {
    const { data } = await stocksApi.getRecommendations({ top_k: 50 })
    recommendations.value = data.items ?? []
    recDate.value = data.date ?? ''
  } catch {
    recommendations.value = []
  } finally {
    recLoading.value = false
  }
})

// ── 공통 유틸 ──────────────────────────────────────────────────
const sentimentKo = (s) => ({
  positive:'긍정', negative:'부정', neutral:'중립',
  긍정:'긍정', 부정:'부정', 중립:'중립',
}[s] ?? '중립')

const sentimentColor = (s) => ({
  긍정:'#065f46', positive:'#065f46',
  부정:'#991b1b', negative:'#991b1b',
  중립:'#374151', neutral:'#374151',
}[s] ?? '#374151')

const formatDate = (dt) => {
  if (!dt) return ''
  try { return new Date(dt).toLocaleDateString('ko-KR', { month:'long', day:'numeric' }) }
  catch { return String(dt).slice(0, 10) }
}

const openUrl = (url) => {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

// ── Mock 데이터 ────────────────────────────────────────────────
const MOCK_RANKINGS = [
  { rank:1, news_id:'m1', provider:'연합뉴스',  title:'삼성전자, AI 반도체 수요 급증에 영업이익 30% 상승',  sentiment_label:'positive', ranking_score:9.87, published_at:'2026-05-26' },
  { rank:2, news_id:'m2', provider:'매일경제',  title:'SK하이닉스 HBM4 양산 돌입…엔비디아 독점 공급 확정', sentiment_label:'positive', ranking_score:9.12, published_at:'2026-05-26' },
  { rank:3, news_id:'m3', provider:'한국경제',  title:'원·달러 환율 1,380원대 안착…수출 기업 실적 기대감',  sentiment_label:'neutral',  ranking_score:8.54, published_at:'2026-05-26' },
  { rank:4, news_id:'m4', provider:'조선비즈',  title:'美 연준 금리 동결…신흥국 증시 일제히 반등',          sentiment_label:'positive', ranking_score:7.91, published_at:'2026-05-26' },
  { rank:5, news_id:'m5', provider:'서울경제',  title:'코스피 2,800선 돌파 시도…외국인 순매수 5거래일 연속', sentiment_label:'positive', ranking_score:7.43, published_at:'2026-05-26' },
]
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>

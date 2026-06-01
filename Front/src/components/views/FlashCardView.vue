<template>
  <div class="w-full h-full relative rounded-[2rem] overflow-hidden"
       style="background:#d4c9a8">

    <!-- ══════════════════════════════
         카드 A — 뉴스 감성 피드
    ══════════════════════════════ -->
    <div class="absolute rounded-[2rem] overflow-hidden flash-card"
         :class="front === 'A' ? 'at-front' : 'at-back'">

      <div class="w-full h-full flex flex-col"
           style="background:#f0e8d0; border:1px solid rgba(0,0,0,0.18); border-radius:inherit; color:#1a1209; font-family:Georgia,'Times New Roman',serif;">

        <!-- 마스트헤드 -->
        <div class="flex-shrink-0 px-4 pt-3" style="border-bottom:3px double #1a1209;">
          <div class="flex items-center justify-between mb-0.5" style="font-family:sans-serif;">
            <span class="text-[9px] uppercase tracking-widest" style="color:#888;">FinBERT Sentiment Analysis</span>
            <div class="flex items-center gap-2">
              <div class="flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-green-600 animate-pulse inline-block"></span>
                <span class="text-[9px] font-bold uppercase tracking-widest" style="color:#2d6a2d;">LIVE</span>
              </div>
              <button @click="flip"
                      class="flex items-center gap-1 px-2 py-0.5 active:scale-95 transition-all"
                      style="background:#1a1209; color:#f0e8d0; border-radius:3px; font-size:10px; font-weight:700; letter-spacing:0.05em;">
                랭킹
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/>
                  <path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>
                </svg>
              </button>
            </div>
          </div>
          <h2 class="text-center font-black py-1 tracking-tight"
              style="font-size:20px; border-top:2px solid #1a1209; border-bottom:1px solid #1a1209;">
            뉴스 감성 피드
          </h2>
          <!-- 섹션 필터 탭 -->
          <div class="flex gap-0 py-1.5" style="font-family:sans-serif; border-bottom:2px solid #1a1209;">
            <button v-for="f in ['전체','긍정','중립','부정']" :key="f"
                    @click="newsFilter = f"
                    class="flex-1 py-0.5 text-[10px] font-bold transition-all duration-150"
                    :style="newsFilter === f
                      ? 'background:#1a1209; color:#f0e8d0;'
                      : 'background:transparent; color:#888;'">
              {{ f }}
            </button>
          </div>
        </div>

        <!-- 뉴스 리스트 -->
        <div class="flex-1 overflow-y-auto">
          <div v-if="newsFeedLoading" class="flex flex-col items-center justify-center h-24 gap-2">
            <span class="text-[13px] italic" style="color:#888;">취재 중...</span>
          </div>
          <div v-else v-for="(item, idx) in filteredFeedNews" :key="item.id"
               class="px-4 py-2.5 cursor-pointer hover:bg-black/5 transition-colors"
               :style="idx < filteredFeedNews.length-1 ? 'border-bottom:1px solid #d4c8a8;' : ''"
               @click="openUrl(item.url)">
            <div class="flex items-center gap-2 mb-0.5" style="font-family:sans-serif;">
              <span class="text-[9px] font-bold uppercase tracking-wide px-1 py-0.5 text-white"
                    :style="{ background: sentimentColor(item.sentiment) }">
                {{ sentimentKo(item.sentiment) }}
              </span>
              <span class="text-[9px] font-mono" style="color:#999;">{{ item.source }}</span>
              <span class="ml-auto text-[9px] font-bold" style="color:#666; font-family:sans-serif;">
                {{ Math.round(item.confidence * 100) }}%
              </span>
            </div>
            <p class="font-bold leading-snug" style="font-size:13px;">{{ item.title }}</p>
            <p class="text-[10px] mt-0.5" style="color:#999; font-family:sans-serif;">{{ formatDate(item.published_at) }}</p>
          </div>
        </div>
      </div>
    </div><!-- /카드 A -->

    <!-- ══════════════════════════════
         카드 B — 뉴스 감성 랭킹
    ══════════════════════════════ -->
    <div class="absolute rounded-[2rem] overflow-hidden flash-card"
         :class="front === 'B' ? 'at-front' : 'at-back'">

      <div class="w-full h-full flex flex-col"
           style="background:#eee8d4; border:1px solid rgba(0,0,0,0.18); border-radius:inherit; color:#1a1209; font-family:Georgia,'Times New Roman',serif;">

        <!-- 마스트헤드 -->
        <div class="flex-shrink-0 px-4 pt-3" style="border-bottom:3px double #1a1209;">
          <div class="flex items-center justify-between mb-0.5" style="font-family:sans-serif;">
            <span class="text-[9px] uppercase tracking-widest" style="color:#888;">FinBERT · Daily Ranking</span>
            <div class="flex items-center gap-2">
              <span v-if="rankingDisplayDate" class="text-[9px]" style="color:#888;">{{ rankingDisplayDate }}</span>
              <button @click="flip"
                      class="flex items-center gap-1 px-2 py-0.5 active:scale-95 transition-all"
                      style="background:#1a1209; color:#eee8d4; border-radius:3px; font-size:10px; font-weight:700; letter-spacing:0.05em;">
                피드
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/>
                  <path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>
                </svg>
              </button>
            </div>
          </div>
          <h2 class="text-center font-black py-1 tracking-tight"
              style="font-size:20px; border-top:2px solid #1a1209; border-bottom:1px solid #1a1209;">
            뉴스 감성 랭킹
          </h2>
          <!-- 섹션 필터 탭 -->
          <div class="flex gap-0 py-1.5" style="font-family:sans-serif; border-bottom:2px solid #1a1209;">
            <button v-for="f in ['전체','긍정','중립','부정']" :key="f"
                    @click="rankingFilter = f"
                    class="flex-1 py-0.5 text-[10px] font-bold transition-all duration-150"
                    :style="rankingFilter === f
                      ? 'background:#1a1209; color:#eee8d4;'
                      : 'background:transparent; color:#888;'">
              {{ f }}
            </button>
          </div>
        </div>

        <!-- 랭킹 리스트 -->
        <div class="flex-1 overflow-y-auto">
          <div v-if="rankingLoading" class="flex flex-col items-center justify-center h-24">
            <span class="text-[13px] italic" style="color:#888;">집계 중...</span>
          </div>
          <div v-else-if="rankingError" class="flex flex-col items-center justify-center h-24 gap-1 text-center px-4">
            <span class="text-[13px] font-bold">데이터 준비 중</span>
            <span class="text-[11px] italic" style="color:#888;">뉴스 DB가 아직 생성되지 않았습니다</span>
          </div>
          <template v-else>
            <div v-for="(item, idx) in (filteredRankingNews.length ? filteredRankingNews : MOCK_RANKINGS)"
                 :key="item.news_id"
                 class="flex items-start gap-3 px-4 py-2.5 cursor-pointer hover:bg-black/5 transition-colors"
                 :style="idx < (filteredRankingNews.length || MOCK_RANKINGS.length)-1 ? 'border-bottom:1px solid #ccc0a0;' : ''"
                 :class="!filteredRankingNews.length ? 'opacity-60' : ''"
                 @click="openUrl(item.origin_url || item.google_url)">
              <!-- 순위 번호 -->
              <span class="flex-shrink-0 font-black text-center leading-none pt-0.5"
                    style="font-size:18px; min-width:20px; font-family:Georgia,serif;"
                    :style="{ color: item.rank <= 3 ? '#9a6e10' : '#bbb' }">
                {{ item.rank }}
              </span>
              <!-- 기사 내용 -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 mb-0.5" style="font-family:sans-serif;">
                  <span class="text-[9px] font-bold uppercase tracking-wide px-1 py-0.5 text-white"
                        :style="{ background: sentimentColor(item.sentiment_label) }">
                    {{ sentimentKo(item.sentiment_label) }}
                  </span>
                  <span class="text-[9px] font-mono truncate" style="color:#999;">{{ item.provider }}</span>
                  <span class="ml-auto text-[9px] font-bold flex-shrink-0" style="color:#9a6e10; font-family:sans-serif;">
                    {{ (item.ranking_score ?? 0).toFixed(1) }}pt
                  </span>
                </div>
                <p class="font-bold leading-snug" style="font-size:13px;">{{ item.title }}</p>
                <p class="text-[10px] mt-0.5" style="color:#999; font-family:sans-serif;">{{ formatDate(item.published_at) }}</p>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div><!-- /카드 B -->


  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useNewsFeed, useNewsRankings } from '@/composables/useStockQuery.js'

const front = ref('A')
const flip = () => { front.value = front.value === 'A' ? 'B' : 'A' }

// ── 카드 A: 뉴스 감성 피드 ─────────────────────────────────────────
const newsFilter   = ref('전체')
const feedParams   = ref({ limit: 30 })
const { data: newsFeedData, isLoading: newsFeedLoading } = useNewsFeed(feedParams)

const feedList = computed(() => {
  const raw = newsFeedData.value?.items ?? newsFeedData.value ?? []
  if (raw.length) return raw
  return MOCK_FEED
})

const filteredFeedNews = computed(() =>
  newsFilter.value === '전체'
    ? feedList.value
    : feedList.value.filter(n => sentimentKo(n.sentiment ?? n.sentiment_label) === newsFilter.value)
)

// ── 카드 B: 뉴스 감성 랭킹 ─────────────────────────────────────────
const rankingFilter = ref('전체')
const rankingParams = ref({ limit: 30 })
const {
  data:      rankingData,
  isLoading: rankingLoading,
  isError:   rankingError,
} = useNewsRankings(rankingParams)

const rankingDisplayDate = computed(() => rankingData.value?.display_date ?? null)

const rankingList = computed(() => rankingData.value?.items ?? [])

const filteredRankingNews = computed(() =>
  rankingFilter.value === '전체'
    ? rankingList.value
    : rankingList.value.filter(n => sentimentKo(n.sentiment_label) === rankingFilter.value)
)

// ── 공통 유틸 ─────────────────────────────────────────────────────
const sentimentKo = (s) => ({
  positive: '긍정', negative: '부정', neutral: '중립',
  긍정: '긍정', 부정: '부정', 중립: '중립',
}[s] ?? '중립')

const sentimentColor = (s) => ({
  긍정: '#065f46', positive: '#065f46',
  부정: '#991b1b', negative: '#991b1b',
  중립: '#374151', neutral: '#374151',
}[s] ?? '#374151')

const sentimentStyle = (s) => {
  const key = sentimentKo(s)
  return {
    '긍정': { background: 'rgba(52,211,153,0.18)',  color: '#34d399', border: '1px solid rgba(52,211,153,0.3)'  },
    '중립': { background: 'rgba(148,163,184,0.15)', color: '#94a3b8', border: '1px solid rgba(148,163,184,0.22)' },
    '부정': { background: 'rgba(248,113,113,0.18)', color: '#f87171', border: '1px solid rgba(248,113,113,0.3)'  },
  }[key] ?? { background: 'rgba(255,255,255,0.1)', color: '#fff' }
}

const rankBadgeStyle = (rank) => {
  if (rank === 1) return { background: 'rgba(251,191,36,0.25)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.4)' }
  if (rank === 2) return { background: 'rgba(148,163,184,0.2)', color: '#94a3b8', border: '1px solid rgba(148,163,184,0.3)' }
  if (rank === 3) return { background: 'rgba(180,120,60,0.2)',  color: '#cd7f32', border: '1px solid rgba(180,120,60,0.35)' }
  return { background: 'rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.4)', border: '1px solid rgba(255,255,255,0.12)' }
}

const formatDate = (dt) => {
  if (!dt) return ''
  try {
    return new Date(dt).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
  } catch {
    return String(dt).slice(0, 10)
  }
}

const openUrl = (url) => {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

const activeFilterStyle = (f) => ({
  '전체': { background: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.9)',  border: '1px solid rgba(255,255,255,0.28)' },
  '긍정': { background: 'rgba(52,211,153,0.2)',   color: '#34d399',                border: '1px solid rgba(52,211,153,0.4)'  },
  '중립': { background: 'rgba(148,163,184,0.2)',  color: '#94a3b8',                border: '1px solid rgba(148,163,184,0.35)' },
  '부정': { background: 'rgba(248,113,113,0.2)',  color: '#f87171',                border: '1px solid rgba(248,113,113,0.4)'  },
}[f] ?? {})

const inactiveFilterStyle = 'background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.45);border:1px solid rgba(255,255,255,0.12)'

// ── Fallback 목업 데이터 ───────────────────────────────────────────
const MOCK_FEED = [
  { id: 1,  source: '연합뉴스',     sentiment: 'positive', title: 'BNP파리바, 韓 성장률 2.7%로 상향…한은 이른 금리인상 검토',    published_at: '2026-05-26', confidence: 0.94 },
  { id: 2,  source: '중앙일보',     sentiment: 'positive', title: '융인대, AI 기본교육과정 개발 지원 사업 선정',                  published_at: '2026-05-26', confidence: 1.00 },
  { id: 3,  source: '연합인포맥스', sentiment: 'neutral',  title: '한국·일본·대만 증시, 일제히 사상 최고치 다시 써',             published_at: '2026-05-26', confidence: 0.01 },
  { id: 4,  source: 'cio.com',      sentiment: 'neutral',  title: '"보도자료도 AI 친화적으로" 행안부, 마크다운 도입 추진',        published_at: '2026-05-26', confidence: 0.00 },
  { id: 5,  source: '한국NGO신문',  sentiment: 'neutral',  title: '글로벌경제문화포럼(GECF), 4월 정기모임 성황리 개최',          published_at: '2026-05-26', confidence: 0.00 },
]

const MOCK_RANKINGS = [
  { rank: 1, news_id: 'mock-1', provider: '연합뉴스',  title: '삼성전자, AI 반도체 수요 급증에 영업이익 30% 상승',   sentiment_label: 'positive', ranking_score: 9.87, published_at: '2026-05-26' },
  { rank: 2, news_id: 'mock-2', provider: '매일경제',  title: 'SK하이닉스 HBM4 양산 돌입…엔비디아 독점 공급 확정',  sentiment_label: 'positive', ranking_score: 9.12, published_at: '2026-05-26' },
  { rank: 3, news_id: 'mock-3', provider: '한국경제',  title: '원·달러 환율 1,380원대 안착…수출 기업 실적 기대감',   sentiment_label: 'neutral',  ranking_score: 8.54, published_at: '2026-05-26' },
  { rank: 4, news_id: 'mock-4', provider: '조선비즈',  title: '美 연준 금리 동결…신흥국 증시 일제히 반등',           sentiment_label: 'positive', ranking_score: 7.91, published_at: '2026-05-26' },
  { rank: 5, news_id: 'mock-5', provider: '서울경제',  title: '코스피 2,800선 돌파 시도…외국인 순매수 5거래일 연속', sentiment_label: 'positive', ranking_score: 7.43, published_at: '2026-05-26' },
]
</script>

<style scoped>
.flash-card {
  transition:
    top    0.48s cubic-bezier(0.34, 1.38, 0.64, 1),
    left   0.48s cubic-bezier(0.34, 1.38, 0.64, 1),
    right  0.48s cubic-bezier(0.34, 1.38, 0.64, 1),
    bottom 0.48s cubic-bezier(0.34, 1.38, 0.64, 1),
    box-shadow 0.38s ease;
}

.at-front {
  top:    8px;
  left:   0;
  right:  28px;
  bottom: 0;
  z-index: 2;
  box-shadow: 0 14px 44px rgba(0,0,0,0.65), 0 4px 14px rgba(0,0,0,0.45);
}

.at-back {
  top:    0;
  left:   20px;
  right:  0;
  bottom: 8px;
  z-index: 1;
  box-shadow: 0 4px 18px rgba(0,0,0,0.35);
}
</style>

<template>
  <div class="w-full h-full relative rounded-[2rem] overflow-hidden"
       style="background:#04080f">

    <!-- ══════════════════════════════
         카드 B — 뉴스 감성 피드
    ══════════════════════════════ -->
    <div class="absolute rounded-[2rem] overflow-hidden flash-card"
         :class="front === 'B' ? 'at-front' : 'at-back'">

      <div class="w-full h-full flex flex-col text-white"
           style="background:linear-gradient(155deg,#0a0f1e 0%,#060b14 100%); border:1px solid rgba(255,255,255,0.09); border-radius:inherit">

        <!-- 헤더 -->
        <div class="px-4 pt-4 pb-3 border-b border-white/10 flex-shrink-0 flex items-center justify-between"
             :class="front === 'B' ? 'pr-[62px]' : 'pr-4'">
          <div>
            <p class="text-[8px] text-white/35 font-mono tracking-widest uppercase mb-0.5">FinBERT Sentiment</p>
            <h2 class="text-lg font-black text-white tracking-tight leading-none">뉴스 감성 피드</h2>
          </div>
          <div class="px-2 py-0.5 rounded-full flex-shrink-0"
               style="background:rgba(52,211,153,0.15); border:1px solid rgba(52,211,153,0.35)">
            <span class="text-[9px] font-bold" style="color:#34d399">LIVE</span>
          </div>
        </div>

        <!-- 검색 바 -->
        <div class="px-3 pt-2.5 pb-0 flex-shrink-0">
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg"
               style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1)">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
                 stroke="rgba(255,255,255,0.3)" stroke-width="2.5">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <span class="text-[10px]" style="color:rgba(255,255,255,0.28)">종목 티커 검색 (예: 005930)</span>
          </div>
        </div>

        <!-- 필터 탭 -->
        <div class="px-3 pt-2 pb-2 flex gap-1.5 flex-shrink-0">
          <button v-for="f in ['전체','긍정','중립','부정']" :key="f"
                  @click="newsFilter = f"
                  class="px-2.5 py-1 rounded-full text-[9px] font-bold transition-all duration-150"
                  :style="newsFilter === f ? activeFilterStyle(f) : inactiveFilterStyle">
            {{ f }}
          </button>
        </div>

        <!-- 뉴스 리스트 -->
        <div class="flex-1 overflow-y-auto px-3 pb-3 space-y-1.5">
          <div v-for="item in filteredNews" :key="item.id"
               class="p-2.5 rounded-xl cursor-pointer transition-colors duration-150"
               style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08)">
            <div class="flex items-center gap-1.5 mb-1">
              <span class="text-[8px] font-mono" style="color:rgba(255,255,255,0.35)">{{ item.source }}</span>
              <span class="px-1.5 py-0.5 rounded text-[7.5px] font-bold" :style="sentimentStyle(item.sentiment)">
                {{ item.sentiment }}
              </span>
              <span class="ml-auto text-[8px] font-mono"
                    :style="{ color: item.confidence >= 50 ? 'rgba(52,211,153,0.7)' : 'rgba(255,255,255,0.25)' }">
                신뢰도 {{ item.confidence }}%
              </span>
            </div>
            <p class="text-[11px] font-semibold leading-snug" style="color:rgba(255,255,255,0.88)">{{ item.title }}</p>
            <p class="text-[8.5px] mt-0.5 font-mono" style="color:rgba(255,255,255,0.28)">{{ item.date }}</p>
          </div>
        </div>
      </div>
    </div><!-- /카드 B -->

    <!-- ══════════════════════════════
         카드 A — 시장 대시보드
    ══════════════════════════════ -->
    <div class="absolute rounded-[2rem] overflow-hidden flash-card"
         :class="front === 'A' ? 'at-front' : 'at-back'">

      <div class="w-full h-full flex flex-col text-white"
           style="background:linear-gradient(155deg,#0a0f1a 0%,#060b12 100%); border:1px solid rgba(255,255,255,0.09); border-radius:inherit">

        <!-- 헤더 -->
        <div class="px-4 pt-4 pb-3 border-b border-white/10 flex-shrink-0 flex items-start justify-between"
             :class="front === 'A' ? 'pr-[62px]' : 'pr-4'">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="px-2 py-0.5 rounded-full text-[8.5px] font-bold"
                    style="background:rgba(52,211,153,0.15); color:#34d399; border:1px solid rgba(52,211,153,0.3)">
                맑음 ☀
              </span>
              <span class="text-[9px] font-bold tracking-wide" style="color:rgba(255,255,255,0.55)">강세장</span>
            </div>
            <p class="text-[9px] leading-snug" style="color:rgba(255,255,255,0.35)">상승 모멘텀 강함 · 적극적 투자 유리</p>
          </div>
          <div class="text-right flex-shrink-0">
            <p class="text-2xl font-black leading-none" style="color:#34d399">
              20.0<span class="text-sm font-bold">%</span>
            </p>
            <p class="text-[8px] mt-0.5" style="color:rgba(255,255,255,0.35)">Tier A 비율</p>
          </div>
        </div>

        <!-- 통계 3개 -->
        <div class="grid grid-cols-3 border-b border-white/10 flex-shrink-0">
          <div class="px-3 py-2.5 border-r border-white/10">
            <p class="text-[7.5px] mb-0.5" style="color:rgba(255,255,255,0.35)">분석 종목</p>
            <p class="text-[13px] font-black text-white">2,317
              <span class="text-[8.5px] font-normal" style="color:rgba(255,255,255,0.4)">종목</span>
            </p>
          </div>
          <div class="px-3 py-2.5 border-r border-white/10">
            <p class="text-[7.5px] mb-0.5" style="color:rgba(255,255,255,0.35)">Tier A 종목</p>
            <p class="text-[13px] font-black text-white">463
              <span class="text-[8.5px] font-normal" style="color:rgba(255,255,255,0.4)">종목</span>
            </p>
          </div>
          <div class="px-3 py-2.5">
            <p class="text-[7.5px] mb-0.5" style="color:rgba(255,255,255,0.35)">Tier A 비율</p>
            <p class="text-[13px] font-black" style="color:#34d399">20.0
              <span class="text-[8.5px] font-normal">%</span>
            </p>
          </div>
        </div>

        <!-- 섹터별 현황 + Top5 -->
        <div class="flex-1 overflow-y-auto">

          <!-- 섹터별 현황 -->
          <div class="px-3 pt-2.5 pb-1">
            <p class="text-[8px] font-mono tracking-widest uppercase mb-1.5" style="color:rgba(255,255,255,0.35)">섹터별 현황</p>

            <!-- 컬럼 헤더 -->
            <div class="grid mb-0.5 px-0.5" style="grid-template-columns:1fr 2.2rem 2.8rem 2.2rem 1.8rem; gap:0 4px">
              <span class="text-[7px] uppercase" style="color:rgba(255,255,255,0.22)">섹터</span>
              <span class="text-[7px] text-right uppercase" style="color:rgba(255,255,255,0.22)">종목</span>
              <span class="text-[7px] text-right uppercase" style="color:rgba(255,255,255,0.22)">평균점</span>
              <span class="text-[7px] text-right uppercase" style="color:rgba(255,255,255,0.22)">최고</span>
              <span class="text-[7px] text-right uppercase" style="color:rgba(255,255,255,0.22)">A</span>
            </div>

            <div v-for="s in sectors" :key="s.name"
                 class="grid py-1 border-b px-0.5"
                 style="grid-template-columns:1fr 2.2rem 2.8rem 2.2rem 1.8rem; gap:0 4px; border-color:rgba(255,255,255,0.06)">
              <span class="text-[10px] truncate" style="color:rgba(255,255,255,0.72)">{{ s.name }}</span>
              <span class="text-[9px] text-right font-mono" style="color:rgba(255,255,255,0.42)">{{ s.count }}</span>
              <div class="flex items-center justify-end gap-1">
                <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      :style="{ background: scoreColor(s.avg) }"></span>
                <span class="text-[9px] font-mono" style="color:rgba(255,255,255,0.7)">{{ s.avg }}</span>
              </div>
              <span class="text-[9px] text-right font-mono" style="color:rgba(255,255,255,0.42)">{{ s.max }}</span>
              <span class="text-[9px] font-bold text-right" style="color:#34d399">{{ s.tierA }}</span>
            </div>
          </div>

          <!-- 오늘의 Top 5 -->
          <div class="px-3 pt-2.5 pb-3">
            <p class="text-[8px] font-mono tracking-widest uppercase mb-2" style="color:rgba(255,255,255,0.35)">오늘의 Top 5</p>

            <div v-for="(stock, idx) in top5" :key="stock.code"
                 class="flex items-center gap-2 py-1.5 border-b"
                 style="border-color:rgba(255,255,255,0.06)">
              <span class="text-[9px] font-mono w-3.5 flex-shrink-0" style="color:rgba(255,255,255,0.25)">{{ idx + 1 }}</span>
              <div class="flex-1 min-w-0">
                <p class="text-[10px] font-bold truncate" style="color:rgba(255,255,255,0.85)">{{ stock.name }}</p>
                <p class="text-[8px] font-mono" style="color:rgba(255,255,255,0.3)">{{ stock.code }}</p>
              </div>
              <div class="w-14 h-1 rounded-full overflow-hidden flex-shrink-0"
                   style="background:rgba(255,255,255,0.1)">
                <div class="h-full rounded-full transition-all"
                     :style="{ width: stock.score + '%', background: '#34d399' }"></div>
              </div>
              <span class="text-[9px] font-bold flex-shrink-0" style="color:#34d399">{{ stock.score }}</span>
              <span class="text-[8px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                    style="background:rgba(52,211,153,0.18); color:#34d399; border:1px solid rgba(52,211,153,0.3)">A</span>
            </div>
          </div>
        </div>
      </div>
    </div><!-- /카드 A -->

    <!-- ══════════════════════════════
         넘기기 버튼 — 오른쪽 상단 고정 (z-50)
    ══════════════════════════════ -->
    <button
      @click="flip"
      class="absolute flex items-center gap-1.5
             px-3 py-1.5 rounded-full
             bg-white/12 hover:bg-white/22 active:scale-95
             border border-white/15
             text-[10px] font-bold text-white/70 uppercase tracking-wide
             transition-all duration-150 focus:outline-none"
      style="top:14px; right:12px; z-index:50"
    >
      넘기기
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/>
        <path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>
      </svg>
    </button>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMarketStore } from '@/stores/market.js'
import { useNewsFeed } from '@/composables/useStockQuery.js'

const front = ref('A')
const newsFilter = ref('전체')
const marketStore = useMarketStore()

const flip = () => { front.value = front.value === 'A' ? 'B' : 'A' }

// ── 카드 A: 시장 데이터 ─────────────────────────
onMounted(async () => {
  if (!marketStore.sectorSummary.length) await marketStore.fetchSectorSummary()
  if (!marketStore.topStocks.length)     await marketStore.fetchTopStocks(5)
})

const sectors = computed(() => {
  if (marketStore.sectorSummary.length) {
    return marketStore.sectorSummary
      .sort((a, b) => b.avg_score - a.avg_score)
      .slice(0, 10)
      .map(s => ({
        name:   s.sector,
        count:  s.total_count ?? 0,
        avg:    s.avg_score ?? 0,
        max:    s.max_score ?? 0,
        tierA:  s.a_tier_count ?? 0,
      }))
  }
  return MOCK_SECTORS
})

const top5 = computed(() => {
  if (marketStore.topStocks.length) {
    return marketStore.topStocks.slice(0, 5).map(s => ({
      name:  s.name ?? s.ticker,
      code:  s.ticker,
      score: Math.round(s.score ?? s.composite_score ?? 0),
    }))
  }
  return MOCK_TOP5
})

// ── 카드 B: 뉴스 피드 ──────────────────────────
const newsFeedParams = ref({ limit: 20 })
const { data: newsFeedData } = useNewsFeed(newsFeedParams)

const newsList = computed(() => {
  const raw = newsFeedData.value?.items ?? newsFeedData.value ?? []
  if (raw.length) {
    return raw.map((n, i) => ({
      id:         n.id ?? i,
      source:     n.source ?? n.publisher ?? '',
      sentiment:  n.sentiment_label ?? (n.sentiment_score > 0.5 ? '긍정' : n.sentiment_score < -0.5 ? '부정' : '중립'),
      title:      n.title ?? '',
      date:       n.published_at ? new Date(n.published_at).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' }) : '',
      confidence: Math.round((n.sentiment_confidence ?? Math.abs(n.sentiment_score ?? 0)) * 100),
    }))
  }
  return MOCK_NEWS
})

const filteredNews = computed(() =>
  newsFilter.value === '전체'
    ? newsList.value
    : newsList.value.filter(n => n.sentiment === newsFilter.value)
)

// ── Fallback 목업 데이터 ─────────────────────────
const MOCK_SECTORS = [
  { name: '에너지',       count: 38,  avg: 61.2, max: 99.5,  tierA: 12  },
  { name: 'IT',           count: 645, avg: 59.5, max: 100.0, tierA: 170 },
  { name: '건강관리',     count: 305, avg: 52.6, max: 99.9,  tierA: 67  },
  { name: '산업재',       count: 364, avg: 51.9, max: 99.7,  tierA: 98  },
  { name: '커뮤니케이션', count: 118, avg: 49.7, max: 98.4,  tierA: 14  },
  { name: '경기소비재',   count: 353, avg: 46.4, max: 99.7,  tierA: 50  },
  { name: '소재',         count: 223, avg: 41.8, max: 99.2,  tierA: 29  },
  { name: '유틸리티',     count: 18,  avg: 38.3, max: 94.0,  tierA: 1   },
  { name: '필수소비재',   count: 98,  avg: 32.4, max: 98.2,  tierA: 9   },
  { name: '금융',         count: 155, avg: 31.0, max: 97.2,  tierA: 13  },
]

const MOCK_TOP5 = [
  { name: '제이케이시냅스',  code: '060230', score: 100 },
  { name: '미디어젠',        code: '279600', score: 100 },
  { name: '티엔알바이오팹',  code: '246710', score: 100 },
  { name: '캐리',            code: '313760', score: 100 },
  { name: '엑셀세라퓨틱스',  code: '373110', score: 100 },
]

const MOCK_NEWS = [
  { id: 1,  source: '중앙일보',     sentiment: '긍정', title: '융인대, AI 기본교육과정 개발 지원 사업 선정',               date: '4월 27일', confidence: 100 },
  { id: 2,  source: '한국NGO신문',  sentiment: '중립', title: '글로벌경제문화포럼(GECF), 4월 정기모임 성황리 개최',       date: '4월 27일', confidence: 0   },
  { id: 3,  source: 'cio.com',      sentiment: '중립', title: '"보도자료도 AI 친화적으로" 행안부, 마크다운 도입 추진',    date: '4월 27일', confidence: 0   },
  { id: 4,  source: '연합뉴스',     sentiment: '중립', title: '한국·일본·대만 증시, 일제히 사상 최고치 다시 써',         date: '4월 27일', confidence: 1   },
  { id: 5,  source: '연합인포맥스', sentiment: '긍정', title: 'BNP파리바, 韓 성장률 2.7%로 상향..."한은, 이른 금리인상 검토"', date: '4월 27일', confidence: 94 },
]

const scoreColor = (avg) => {
  if (avg >= 55) return '#34d399';
  if (avg >= 42) return '#fbbf24';
  return '#f87171';
};

const sentimentStyle = (s) => {
  const m = {
    '긍정': { background: 'rgba(52,211,153,0.18)',  color: '#34d399', border: '1px solid rgba(52,211,153,0.3)'  },
    '중립': { background: 'rgba(148,163,184,0.15)', color: '#94a3b8', border: '1px solid rgba(148,163,184,0.22)' },
    '부정': { background: 'rgba(248,113,113,0.18)', color: '#f87171', border: '1px solid rgba(248,113,113,0.3)'  },
  };
  return m[s] ?? { background: 'rgba(255,255,255,0.1)', color: '#fff' };
};

const activeFilterStyle = (f) => {
  const m = {
    '전체': { background: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.9)',  border: '1px solid rgba(255,255,255,0.28)' },
    '긍정': { background: 'rgba(52,211,153,0.2)',   color: '#34d399',                 border: '1px solid rgba(52,211,153,0.4)'  },
    '중립': { background: 'rgba(148,163,184,0.2)',  color: '#94a3b8',                 border: '1px solid rgba(148,163,184,0.35)' },
    '부정': { background: 'rgba(248,113,113,0.2)',  color: '#f87171',                 border: '1px solid rgba(248,113,113,0.4)'  },
  };
  return m[f] ?? {};
};

const inactiveFilterStyle = 'background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.45);border:1px solid rgba(255,255,255,0.12)';
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

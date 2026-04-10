<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { stocksApi, screenerApi, type StockScore, type SectorSummaryItem, type ScreenerItem, type SearchResult } from '../api'

const router = useRouter()

// ── State ────────────────────────────────────────────────────────────────
const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const searchLoading = ref(false)
const showSearch = ref(false)

const recommendations = ref<StockScore[]>([])
const recLoading = ref(true)
const recDate = ref('')
const activeTab = ref<'all' | 'A' | 'B'>('A')

const topPicks = ref<ScreenerItem[]>([])
const sectors = ref<SectorSummaryItem[]>([])
const sectorsLoading = ref(true)

const activeFaq = ref<string | null>(null)
const activeFaqCat = ref('usage')

// ── Computed ─────────────────────────────────────────────────────────────
const filteredRecs = computed(() => {
  if (activeTab.value === 'all') return recommendations.value.slice(0, 10)
  return recommendations.value.filter(r => r.tier === activeTab.value).slice(0, 10)
})

const marketScore = computed(() => {
  if (!recommendations.value.length) return 0
  const top = recommendations.value.slice(0, 50)
  return Math.round(top.reduce((s, r) => s + r.score, 0) / top.length)
})

const marketLabel = computed(() => {
  const s = marketScore.value
  if (s >= 80) return '강세'
  if (s >= 65) return '양호'
  if (s >= 50) return '보통'
  if (s >= 35) return '약세'
  return '침체'
})

// ── Methods ──────────────────────────────────────────────────────────────
let searchTimer: ReturnType<typeof setTimeout>

function onSearchBlur() {
  setTimeout(() => { showSearch.value = false }, 200)
}

function onSearchInput() {
  clearTimeout(searchTimer)
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    showSearch.value = false
    return
  }
  searchLoading.value = true
  showSearch.value = true
  searchTimer = setTimeout(async () => {
    try {
      const { data } = await stocksApi.search(searchQuery.value.trim(), 10)
      searchResults.value = data.items
    } catch {
      searchResults.value = []
    } finally {
      searchLoading.value = false
    }
  }, 300)
}

function goToStock(ticker: string) {
  showSearch.value = false
  searchQuery.value = ''
  router.push(`/stock/${ticker}`)
}

function scoreWidth(score?: number) {
  return `${Math.round(score ?? 0)}%`
}

async function loadRecommendations() {
  recLoading.value = true
  try {
    const { data } = await stocksApi.recommendations({ top_k: 100 })
    recommendations.value = data.items
    recDate.value = data.date
  } catch {
    recommendations.value = []
  } finally {
    recLoading.value = false
  }
}

async function loadTopPicks() {
  try {
    const { data } = await screenerApi.screen({ tier: 'A', limit: 10, sort_by: 'composite_score' })
    topPicks.value = data.items
  } catch {
    topPicks.value = []
  }
}

async function loadSectors() {
  sectorsLoading.value = true
  try {
    const { data } = await stocksApi.sectorSummary()
    sectors.value = data.items.slice(0, 6)
  } catch {
    sectors.value = []
  } finally {
    sectorsLoading.value = false
  }
}

function toggleFaq(id: string) {
  activeFaq.value = activeFaq.value === id ? null : id
}

// Static Korean market indices (placeholder — integrate real-time data source separately)
const indices = [
  { name: 'KOSPI', value: '2,504.61', change: '+12.34', up: true },
  { name: 'KOSDAQ', value: '721.35', change: '-3.20', up: false },
  { name: 'USD/KRW', value: '1,365', change: '+2.5', up: true },
  { name: 'KOSPI200', value: '332.41', change: '+1.82', up: true },
  { name: 'WTI', value: '78.62', change: '-0.31', up: false },
]

const faqs = {
  usage: [
    { id: 'f1', q: 'AI 점수는 어떻게 계산되나요?', a: 'LightGBM, XGBoost, CatBoost 앙상블 모델의 예측 확률 평균을 날짜별 퍼센타일 랭킹(1~100)으로 환산합니다. 80점 이상은 A티어, 60~79점은 B티어입니다.' },
    { id: 'f2', q: '복합 스코어(Composite Score)란?', a: 'ML 점수 60% + 재무 점수 40%를 합산한 종합 투자 매력도입니다. ROE, 부채비율, 영업이익률 등 6개 재무지표를 퍼센타일로 환산해 가중 합산합니다.' },
    { id: 'f3', q: '데이터는 언제 업데이트되나요?', a: '모델 예측 데이터는 사전에 계산되어 DuckDB에 저장됩니다. 신규 데이터 적재 후 precompute 스크립트를 실행하면 반영됩니다.' },
  ],
  screener: [
    { id: 'f4', q: '스크리너에서 어떤 조건을 설정할 수 있나요?', a: 'ML 점수, 티어, 섹터, PER, PBR, ROE, 부채비율, 영업이익률, 매출성장률, 재무 스코어 등 다양한 조건을 복합 적용할 수 있습니다.' },
    { id: 'f5', q: '정렬 기준을 바꿀 수 있나요?', a: '복합 스코어(기본), ML 점수, 재무 스코어, ROE 기준으로 정렬할 수 있습니다.' },
  ],
  chart: [
    { id: 'f6', q: '차트에서 이동평균선은 어떻게 계산되나요?', a: 'MA5, MA20, MA60, MA120이 제공됩니다. 종목별 누적 데이터를 기반으로 롤링 평균을 계산합니다.' },
    { id: 'f7', q: '조회 가능한 기간은 얼마나 되나요?', a: '1개월, 3개월, 6개월, 1년, 3년, 전체 기간을 선택할 수 있습니다.' },
  ],
}

onMounted(() => {
  loadRecommendations()
  loadTopPicks()
  loadSectors()
})
</script>

<template>
  <div>
    <!-- Header -->
    <header class="app-header">
      <RouterLink to="/" class="app-header__logo">
        <div class="app-header__logo-icon">📈</div>
        <span class="app-header__logo-text">스마트스탁</span>
      </RouterLink>
      <div class="app-header__right">
        <RouterLink to="/recommend" class="app-header__btn">추천보기</RouterLink>
      </div>
    </header>

    <!-- Search -->
    <div class="search-wrap" style="position:relative;">
      <div class="search-box">
        <span class="search-box__icon">🔍</span>
        <input
          v-model="searchQuery"
          class="search-box__input"
          placeholder="종목명 또는 코드를 입력하세요"
          @input="onSearchInput"
          @focus="showSearch = searchResults.length > 0"
          @blur="onSearchBlur"
        />
        <div v-if="searchLoading" class="spinner" style="width:18px;height:18px;border-width:2px;"></div>
      </div>

      <Transition name="fade">
        <div v-if="showSearch && searchResults.length" class="search-dropdown">
          <div
            v-for="item in searchResults"
            :key="item.ticker"
            class="search-item"
            @mousedown.prevent="goToStock(item.ticker)"
          >
            <span class="search-item__ticker">{{ item.ticker }}</span>
            <span class="search-item__name">{{ item.name ?? item.ticker }}</span>
            <span v-if="item.score" class="search-item__score">{{ Math.round(item.score) }}점</span>
            <span v-if="item.tier" class="tier-badge" :class="item.tier">{{ item.tier }}</span>
          </div>
        </div>
        <div v-else-if="showSearch && !searchLoading && searchQuery" class="search-dropdown">
          <div class="empty-state" style="padding:20px;">
            <span>"{{ searchQuery }}"에 대한 결과가 없습니다.</span>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Morning briefing -->
    <div class="morning-briefing">
      <span class="morning-briefing__badge">AI 분석</span>
      <span class="morning-briefing__text">
        {{ recDate ? recDate + ' 기준' : '데이터 로딩 중...' }}
        &nbsp;·&nbsp;
        총 {{ recommendations.length }}개 종목 분석 완료
      </span>
    </div>

    <!-- Market score -->
    <div class="market-score" @click="router.push('/recommend')">
      <div class="market-score__left">
        <p class="market-score__title">AI 마켓 스코어</p>
        <p class="market-score__value"><span>{{ marketScore }}</span>점</p>
        <p class="market-score__label">현재 시장 상태: <strong>{{ marketLabel }}</strong></p>
      </div>
      <div>
        <div class="market-score__mini-chart">
          <div
            v-for="i in 8"
            :key="i"
            class="market-score__mini-bar"
            :class="{ active: i <= Math.round(marketScore / 12.5) }"
            :style="{ height: (20 + i * 6) + 'px' }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Korean Indices -->
    <div class="index-group">
      <div class="index-scroll">
        <div v-for="idx in indices" :key="idx.name" class="index-card">
          <p class="index-card__name">{{ idx.name }}</p>
          <p class="index-card__value">{{ idx.value }}</p>
          <p class="index-card__change" :class="idx.up ? 'up' : 'down'">
            <span>{{ idx.up ? '▲' : '▼' }}</span>
            {{ idx.change }}
          </p>
        </div>
      </div>
      <p class="index-date">{{ recDate || '—' }} 기준 (AI 분석일)</p>
    </div>

    <!-- Top Recommended Stocks -->
    <section>
      <div class="section-header">
        <h2>AI 추천 종목</h2>
        <RouterLink to="/recommend" class="section-header__more">
          더보기
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 3L11.2 8.2L6.4 13" stroke="#8C98A7" stroke-width="1.4" stroke-linecap="round"/></svg>
        </RouterLink>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button class="tab-btn" :class="{ active: activeTab === 'A' }" @click="activeTab = 'A'">A 티어</button>
        <button class="tab-btn" :class="{ active: activeTab === 'B' }" @click="activeTab = 'B'">B 티어</button>
        <button class="tab-btn" :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">전체 TOP10</button>
      </div>

      <div v-if="recLoading" class="loading-spinner"><div class="spinner"></div></div>

      <div v-else-if="filteredRecs.length" class="stock-list">
        <div
          v-for="(stock, i) in filteredRecs"
          :key="stock.ticker"
          class="stock-item"
          @click="router.push(`/stock/${stock.ticker}`)"
        >
          <span class="stock-item__rank">{{ i + 1 }}</span>
          <div class="stock-item__logo">
            <span>{{ stock.name?.[0] ?? stock.ticker[0] }}</span>
          </div>
          <div class="stock-item__info">
            <p class="stock-item__name">{{ stock.name ?? stock.ticker }}</p>
            <div class="stock-item__meta">
              <span class="stock-item__ticker">{{ stock.ticker }}</span>
              <span class="stock-item__sector" v-if="stock.sector">· {{ stock.sector }}</span>
            </div>
          </div>
          <div class="stock-item__right">
            <p class="stock-item__score-num">{{ Math.round(stock.score) }}</p>
            <div class="score-bar stock-item__scorebar">
              <div class="score-bar__fill" :style="{ width: scoreWidth(stock.score) }"></div>
            </div>
            <p class="stock-item__score-label">ML 점수</p>
          </div>
          <span class="tier-badge" :class="stock.tier">{{ stock.tier }}</span>
        </div>

        <RouterLink to="/recommend" class="more-btn">
          더보기
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 3L11.2 8.2L6.4 13" stroke="#8C98A7" stroke-width="1.4" stroke-linecap="round"/></svg>
        </RouterLink>
      </div>

      <div v-else class="empty-state">
        <span class="empty-state__icon">📭</span>
        <span>{{ activeTab }} 티어 종목이 없습니다.</span>
      </div>
    </section>

    <!-- AI Picks Carousel (Top A-tier with composite score) -->
    <section v-if="topPicks.length">
      <div class="section-header">
        <h2>🤖 AI 종합 추천</h2>
        <RouterLink to="/screener" class="section-header__more">
          스크리너
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 3L11.2 8.2L6.4 13" stroke="#8C98A7" stroke-width="1.4" stroke-linecap="round"/></svg>
        </RouterLink>
      </div>
      <div class="ai-picks-scroll">
        <div
          v-for="pick in topPicks"
          :key="pick.ticker"
          class="ai-pick-card"
          @click="router.push(`/stock/${pick.ticker}`)"
        >
          <div class="ai-pick-card__header">
            <div class="ai-pick-card__logo">
              {{ pick.name?.[0] ?? pick.ticker[0] }}
            </div>
            <span class="ai-pick-card__name">{{ pick.name ?? pick.ticker }}</span>
          </div>
          <p class="ai-pick-card__score">{{ Math.round(pick.composite_score ?? pick.score ?? 0) }}</p>
          <div class="score-bar ai-pick-card__score-bar">
            <div class="score-bar__fill" :style="{ width: scoreWidth(pick.composite_score ?? pick.score) }"></div>
          </div>
          <div class="ai-pick-card__footer">
            <span class="ai-pick-card__ticker">{{ pick.ticker }}</span>
            <span class="tier-badge" :class="pick.tier">{{ pick.tier }}</span>
          </div>
          <div style="margin-top:6px; display:flex; justify-content:space-between;">
            <span style="font-size:11px; color:var(--color-text-muted);">ML {{ Math.round(pick.score ?? 0) }}</span>
            <span style="font-size:11px; color:var(--color-text-muted);">재무 {{ Math.round(pick.finance_score ?? 0) }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Sector Summary -->
    <section v-if="sectors.length">
      <div class="section-header">
        <h2>섹터별 현황</h2>
        <RouterLink to="/screener" class="section-header__more">
          스크리너
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 3L11.2 8.2L6.4 13" stroke="#8C98A7" stroke-width="1.4" stroke-linecap="round"/></svg>
        </RouterLink>
      </div>
      <div class="sector-list">
        <div
          v-for="sector in sectors"
          :key="sector.sector"
          class="sector-card"
          @click="router.push(`/screener?sector=${encodeURIComponent(sector.sector)}`)"
        >
          <p class="sector-card__name">{{ sector.sector }}</p>
          <p class="sector-card__score">{{ Math.round(sector.avg_score) }}</p>
          <div class="score-bar" style="margin-bottom:8px;">
            <div class="score-bar__fill" :style="{ width: scoreWidth(sector.avg_score) }"></div>
          </div>
          <div class="sector-card__meta">
            <span class="sector-card__a-tier">A {{ sector.a_tier_count }}종목</span>
            <span>전체 {{ sector.total_count }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Banners -->
    <section>
      <div class="section-header">
        <h2>주요 기능</h2>
      </div>
      <div class="cta-list">
        <RouterLink to="/recommend" class="cta-item">
          <div class="cta-item__icon">⭐</div>
          <div class="cta-item__content">
            <p class="cta-item__subtitle">AI가 추천하는 투자 타이밍</p>
            <p class="cta-item__title">오늘의 AI 추천 종목</p>
          </div>
          <span class="cta-item__arrow">›</span>
        </RouterLink>

        <RouterLink to="/screener" class="cta-item">
          <div class="cta-item__icon">🔍</div>
          <div class="cta-item__content">
            <p class="cta-item__subtitle">ML + 재무지표 다중 조건 검색</p>
            <p class="cta-item__title">종목 스크리너</p>
          </div>
          <span class="cta-item__arrow">›</span>
        </RouterLink>

        <RouterLink to="/compare" class="cta-item">
          <div class="cta-item__icon">⚖️</div>
          <div class="cta-item__content">
            <p class="cta-item__subtitle">ML 점수 이력 + 재무 데이터 비교</p>
            <p class="cta-item__title">종목 비교 분석</p>
          </div>
          <span class="cta-item__arrow">›</span>
        </RouterLink>
      </div>
    </section>

    <!-- FAQ -->
    <section class="faq-section">
      <div class="section-header">
        <h2>자주 묻는 질문</h2>
      </div>
      <div class="faq-categories">
        <button class="faq-cat-btn" :class="{ active: activeFaqCat === 'usage' }" @click="activeFaqCat = 'usage'">AI 점수</button>
        <button class="faq-cat-btn" :class="{ active: activeFaqCat === 'screener' }" @click="activeFaqCat = 'screener'">스크리너</button>
        <button class="faq-cat-btn" :class="{ active: activeFaqCat === 'chart' }" @click="activeFaqCat = 'chart'">차트/재무</button>
      </div>
      <div class="faq-list">
        <div
          v-for="faq in faqs[activeFaqCat as keyof typeof faqs]"
          :key="faq.id"
          class="faq-item"
        >
          <div class="faq-question" @click="toggleFaq(faq.id)">
            <span class="faq-question__text">{{ faq.q }}</span>
            <span class="faq-toggle" :class="{ open: activeFaq === faq.id }">＋</span>
          </div>
          <div class="faq-answer" :class="{ open: activeFaq === faq.id }">
            <div class="faq-answer__inner">{{ faq.a }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Signup banner -->
    <div class="signup-banner">
      <div>
        <p class="signup-banner__label">AI 종목 추천 서비스</p>
        <p class="signup-banner__title">지금 확인하고<br>종목 분석을 시작하세요</p>
      </div>
      <RouterLink to="/recommend" class="signup-banner__btn">
        AI 추천 종목 보기 →
      </RouterLink>
    </div>

    <!-- Footer -->
    <footer class="app-footer">
      <p class="app-footer__title">스마트스탁 AI</p>
      <p class="app-footer__disclaimer">
        이 서비스가 제공하는 모든 정보는 투자 참고용으로만 제공되며 특정 주식 매매를 추천하거나
        투자 결정의 유일한 근거로 사용되어서는 안 됩니다. 모든 투자에는 원금 손실 위험이 따릅니다.
      </p>
      <div class="app-footer__links">
        <span>이용약관</span>
        <span>개인정보처리방침</span>
        <span>GitHub</span>
      </div>
      <p class="app-footer__copy">© 2025 스마트스탁 AI · LightGBM + XGBoost + CatBoost Ensemble</p>
    </footer>
  </div>
</template>

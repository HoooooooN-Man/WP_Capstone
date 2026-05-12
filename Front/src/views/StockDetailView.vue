<script setup lang="ts">
// UX W4 — 종목 상세 화면 재설계.
// 결정 박제 (w4-stock-detail-draft.md):
//   §1 추천 메타: URL query (?from=recommend&model_version=...&cohort=...&diversify=...)
//                   → MetaBadge echo. 직접 진입 시 숨김.
//   §2 권고: realtime endpoint 미사용 (현재 캡스톤 의존도 낮춤), score 추천 응답 또는 history 첫 행.
//   §3 차트 = Line + Volume (Candle 미도입). 6M default.
//   §4 공시: 백엔드 endpoint 부재 → empty state.
//      재무 표·뉴스 Top 10, 외부 link.
//   §5 잘못된 ticker → 404 페이지.
//   §6 lazy composable enabled 패턴, URL ?tab= 동기, staleTime: 차트·재무 1h, 그 외 5m.
//   §7 ARIA 기본 (role=tablist·tab·tabpanel, aria-busy).
//   §8 composable 5 한 commit.

import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import CoverageBadge from '@/components/CoverageBadge.vue'
import MarketRegimeBanner from '@/components/MarketRegimeBanner.vue'
import MetaBadge from '@/components/MetaBadge.vue'
// UX W6B — 캡스톤 차트 자산 (Chart.js + chartjs-chart-financial) 통합.
import CandleChart from '@/components/stockDetail/CandleChart.vue'
import VolumeChart from '@/components/stockDetail/VolumeChart.vue'
import {
  useStockBasic, useStockChart, useStockFinance, useStockNews, useStockDisclosures,
  formatPrice, formatChange, changeClass, formatFinanceQuarter, pickLatest,
} from '@/composables/useStockDetail'
import { COHORT_LABEL, DIVERSIFY_LABEL } from '@/composables/useRecommendations'

// @ts-ignore — 기존 stores
import { useAuthStore } from '@/stores/auth.js'
// @ts-ignore
import { useWatchlistStore } from '@/stores/watchlist.js'

const route   = useRoute()
const router  = useRouter()
const auth    = useAuthStore()
const watch_  = useWatchlistStore()

// ── URL params ─────────────────────────────────────────────────────────────
const ticker = computed(() => String(route.params.ticker ?? ''))

// 추천 컨텍스트 (URL query)
const fromRecommend = computed(() => route.query.from === 'recommend')
const ctxModelVer   = computed(() => (route.query.model_version as string) ?? null)
const ctxCohort     = computed(() => (route.query.cohort        as string) ?? null)
const ctxDiversify  = computed(() => (route.query.diversify     as string) ?? null)

// ── Tab state ──────────────────────────────────────────────────────────────
type TabKey = 'finance' | 'news' | 'disclosures'
const activeTab = computed<TabKey>({
  get: () => ((route.query.tab as TabKey) ?? 'finance'),
  set: v => router.replace({ query: { ...route.query, tab: v } }),
})
const tabEnabled = (key: TabKey) => computed(() => activeTab.value === key)

// ── 데이터 (즉시) ──────────────────────────────────────────────────────────
const basic = useStockBasic(ticker)
const chart = useStockChart(ticker)

// 가장 최근 score·tier 추출 (history 마지막 행)
const latest = computed(() => pickLatest(basic.data.value ?? []))
const stockName   = computed(() => latest.value?.name ?? ticker.value)
const stockSector = computed(() => latest.value?.sector ?? '')
const latestClose = computed(() => latest.value?.close ?? null)
const latestScore = computed(() => latest.value?.score ?? null)
const latestTier  = computed(() => latest.value?.tier  ?? null)

// 등락률 — chart 마지막 2 row 비교
const latestChange = computed<number | null>(() => {
  const rows = chart.data.value ?? []
  if (rows.length < 2) return null
  const last = rows[rows.length - 1].close
  const prev = rows[rows.length - 2].close
  if (!prev) return null
  return ((last - prev) / prev) * 100
})

// market_regime — 추천 컨텍스트 또는 별 endpoint. 현재는 query 에서 못 받으면 normal.
const marketRegime = computed(() => (route.query.regime as string) ?? 'normal')

// coverage_status — 별 endpoint 없으니 history 길이로 derive
const coverageStatus = computed<'ok' | 'insufficient_data'>(() =>
  (basic.data.value?.length ?? 0) >= 60 ? 'ok' : 'insufficient_data',
)
const coverageDays = computed(() => basic.data.value?.length ?? 0)

// ── 데이터 (lazy) ──────────────────────────────────────────────────────────
const finance     = useStockFinance(ticker, tabEnabled('finance'))
const news        = useStockNews(ticker, tabEnabled('news'))
const disclosures = useStockDisclosures(ticker, tabEnabled('disclosures'))

// ── 차트 기간 ──────────────────────────────────────────────────────────────
type Period = '3M' | '6M' | '1Y' | '3Y' | '5Y' | 'All'
const chartPeriod = ref<Period>('6M')
const periodDays: Record<Period, number> = {
  '3M': 90, '6M': 180, '1Y': 365, '3Y': 1095, '5Y': 1825, 'All': Infinity,
}
const chartSlice = computed(() => {
  const all = chart.data.value ?? []
  const days = periodDays[chartPeriod.value]
  if (!isFinite(days)) return all
  return all.slice(-days)
})

// ── 404 분기 (잘못된 ticker) ───────────────────────────────────────────────
const isNotFound = computed(() =>
  !basic.isLoading.value
    && basic.isError.value === false
    && (basic.data.value?.length ?? 0) === 0
    && !!ticker.value,
)

// ── 액션 ──────────────────────────────────────────────────────────────────
const watchedSet = computed(() => new Set<string>(watch_.tickers ?? []))
const isWatched  = computed(() => watchedSet.value.has(ticker.value))

function onWatchToggle() {
  if (!auth.isAuthenticated) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  watch_.toggle?.(ticker.value)
}

function goSearch() {
  router.push('/screener')
}
</script>

<template>
  <div class="stock-detail">
    <MarketRegimeBanner :regime="marketRegime" />

    <!-- 404: 잘못된 ticker -->
    <div v-if="isNotFound" class="stock-detail__not-found">
      <i class="pi pi-search" />
      <h1>종목을 찾을 수 없습니다</h1>
      <p>"{{ ticker }}" 에 해당하는 종목 정보가 없습니다.</p>
      <button class="stock-detail__retry" @click="goSearch">종목 검색</button>
    </div>

    <template v-else>
      <header class="stock-detail__header">
        <div class="stock-detail__identity">
          <h1 class="stock-detail__name">{{ stockName }}</h1>
          <span class="stock-detail__ticker">{{ ticker }}</span>
          <span v-if="stockSector" class="stock-detail__sector">· {{ stockSector }}</span>
          <button
            class="stock-detail__watch"
            :class="{ 'is-watched': isWatched }"
            :aria-label="isWatched ? '관심종목에서 제거' : '관심종목에 추가'"
            @click="onWatchToggle"
          >
            <i :class="['pi', isWatched ? 'pi-bookmark-fill' : 'pi-bookmark']" />
          </button>
        </div>

        <div class="stock-detail__price-row">
          <span class="stock-detail__price">{{ formatPrice(latestClose) }}</span>
          <span
            v-if="latestChange != null"
            :class="['stock-detail__change', changeClass(latestChange)]"
          >
            {{ formatChange(latestChange) }}
          </span>
          <span v-if="latestScore != null && latestTier" class="stock-detail__score">
            {{ latestScore }}점 · {{ latestTier }}
          </span>
        </div>

        <div v-if="fromRecommend" class="stock-detail__meta-row">
          <MetaBadge label="모델" :value="ctxModelVer" />
          <MetaBadge
            label="코호트"
            :value="ctxCohort ? (COHORT_LABEL[ctxCohort] ?? ctxCohort) : null"
          />
          <MetaBadge
            label="다양성"
            :value="ctxDiversify ? (DIVERSIFY_LABEL[ctxDiversify] ?? ctxDiversify) : null"
          />
        </div>

        <CoverageBadge
          :status="coverageStatus"
          :available-days="coverageDays"
        />
      </header>

      <!-- 차트 -->
      <section class="stock-detail__chart" aria-label="가격 차트">
        <div class="stock-detail__period-row">
          <button
            v-for="p in (['3M','6M','1Y','3Y','5Y','All'] as Period[])"
            :key="p"
            :class="['period-btn', { 'is-active': chartPeriod === p }]"
            @click="chartPeriod = p"
          >
            {{ p }}
          </button>
        </div>
        <div v-if="chart.isLoading.value" class="chart-skeleton" aria-busy="true" />
        <div v-else-if="chart.isError.value" class="chart-error" role="alert">
          차트 데이터를 불러오지 못했습니다.
          <button class="stock-detail__retry" @click="chart.refetch()">다시 시도</button>
        </div>
        <div v-else class="chart-stack">
          <!-- UX W6B — Chart.js 통합 (W4 placeholder 메움) -->
          <CandleChart :candles="chartSlice" :ticker="ticker" />
          <VolumeChart :candles="chartSlice" />
        </div>
      </section>

      <!-- 탭 -->
      <nav class="stock-detail__tabs" role="tablist">
        <button
          v-for="t in ['finance','news','disclosures'] as TabKey[]"
          :key="t"
          role="tab"
          :aria-selected="activeTab === t"
          :class="['tab-btn', { 'is-active': activeTab === t }]"
          @click="activeTab = t"
        >
          {{ t === 'finance' ? '재무' : t === 'news' ? '뉴스' : '공시' }}
        </button>
      </nav>

      <section class="stock-detail__tab-body" role="tabpanel">
        <!-- 재무 -->
        <div v-if="activeTab === 'finance'">
          <div v-if="finance.isLoading.value" aria-busy="true">로딩 중...</div>
          <div v-else-if="finance.isError.value" role="alert">
            재무 데이터를 불러오지 못했습니다.
            <button class="stock-detail__retry" @click="finance.refetch()">다시 시도</button>
          </div>
          <div v-else-if="!(finance.data.value?.length)" class="empty-state">
            <p>재무 데이터가 없습니다.</p>
          </div>
          <table v-else class="finance-table">
            <thead>
              <tr>
                <th>분기</th><th>PER</th><th>PBR</th><th>ROE</th>
                <th>부채비율</th><th>영업이익률</th><th>매출성장률</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in finance.data.value ?? []" :key="`${row.year}-${row.quarter}`">
                <td>{{ formatFinanceQuarter(row) }}</td>
                <td>{{ row.per?.toFixed(1) ?? '-' }}</td>
                <td>{{ row.pbr?.toFixed(2) ?? '-' }}</td>
                <td>{{ row.roe?.toFixed(1) ?? '-' }}%</td>
                <td>{{ row.debt_ratio?.toFixed(1) ?? '-' }}%</td>
                <td>{{ row.op_margin?.toFixed(1) ?? '-' }}%</td>
                <td>{{ row.rev_growth_yoy?.toFixed(1) ?? '-' }}%</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 뉴스 -->
        <div v-else-if="activeTab === 'news'">
          <div v-if="news.isLoading.value" aria-busy="true">로딩 중...</div>
          <div v-else-if="news.isError.value" role="alert">
            뉴스를 불러오지 못했습니다.
            <button class="stock-detail__retry" @click="news.refetch()">다시 시도</button>
          </div>
          <div v-else-if="!(news.data.value?.length)" class="empty-state">
            <p>관련 뉴스가 없습니다.</p>
          </div>
          <ul v-else class="news-list">
            <li v-for="n in news.data.value ?? []" :key="n.news_id">
              <a v-if="n.url" :href="n.url" target="_blank" rel="noopener noreferrer">
                {{ n.title }}
              </a>
              <span v-else>{{ n.title }}</span>
              <small>{{ n.source ?? '' }} · {{ n.published_at ?? '' }}</small>
            </li>
          </ul>
        </div>

        <!-- 공시 (백엔드 endpoint 부재 — empty placeholder) -->
        <div v-else-if="activeTab === 'disclosures'">
          <div class="empty-state">
            <i class="pi pi-info-circle" />
            <p>공시 데이터는 추후 제공 예정입니다.</p>
            <small>
              백엔드 disclosures endpoint 부재 — 차차차차기 후보로 박제 (UX 사이클 완료 후).
            </small>
          </div>
        </div>
      </section>

      <footer class="stock-detail__footer">
        <small>본 정보는 자문이 아닙니다.</small>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.stock-detail {
  max-width: var(--layout-max-width);
  margin: 0 auto;
  padding: var(--layout-content-pad);
  font-family: var(--font-sans);
  color: var(--text-primary);
  background: var(--surface-canvas);
}

/* 404 */
.stock-detail__not-found {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-3);
  padding: var(--space-16);
  text-align: center;
}
.stock-detail__not-found i { font-size: 3rem; color: var(--text-tertiary); }
.stock-detail__not-found h1 { margin: 0; font-size: var(--text-2xl); }

/* Header */
.stock-detail__header {
  display: flex; flex-direction: column; gap: var(--space-3);
  padding: var(--space-6) 0 var(--space-4);
}
.stock-detail__identity {
  display: flex; align-items: center; gap: var(--space-2);
  flex-wrap: wrap;
}
.stock-detail__name {
  margin: 0;
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  line-height: var(--leading-tight);
}
.stock-detail__ticker { font-size: var(--text-base); color: var(--text-secondary); }
.stock-detail__sector { font-size: var(--text-base); color: var(--text-secondary); }
.stock-detail__watch {
  margin-left: auto;
  background: transparent; border: 0; cursor: pointer;
  color: var(--text-tertiary);
  font-size: var(--text-xl);
  padding: var(--space-1);
}
.stock-detail__watch.is-watched { color: var(--color-primary-600); }

.stock-detail__price-row {
  display: flex; align-items: baseline; gap: var(--space-3);
}
.stock-detail__price {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1;
}
.stock-detail__change {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}
.stock-detail__change.change--up   { color: var(--color-up); }
.stock-detail__change.change--down { color: var(--color-down); }
.stock-detail__score {
  margin-left: auto;
  font-size: var(--text-base);
  color: var(--text-secondary);
}

.stock-detail__meta-row {
  display: flex; flex-wrap: wrap; gap: var(--space-2);
  margin-top: var(--space-2);
}

/* Chart */
.stock-detail__chart {
  margin-top: var(--space-6);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-sm);
}
.stock-detail__period-row {
  display: flex; gap: var(--space-1);
  margin-bottom: var(--space-3);
}
.period-btn {
  padding: var(--space-1) var(--space-3);
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
}
.period-btn.is-active {
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border-color: var(--color-primary-600);
}
.chart-skeleton {
  height: 400px;
  background: var(--surface-muted);
  border-radius: var(--radius-md);
  animation: shimmer 1.2s infinite;
}
.chart-error {
  height: 400px;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-secondary);
}
.chart-stack {
  display: flex; flex-direction: column; gap: var(--space-2);
}

/* Tabs */
.stock-detail__tabs {
  display: flex;
  gap: var(--space-1);
  margin-top: var(--space-6);
  border-bottom: 1px solid var(--border-default);
}
.tab-btn {
  padding: var(--space-3) var(--space-4);
  background: transparent;
  border: 0; border-bottom: 2px solid transparent;
  font-size: var(--text-base);
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;
}
.tab-btn.is-active {
  color: var(--color-primary-600);
  border-bottom-color: var(--color-primary-600);
  font-weight: var(--font-semibold);
}
.tab-btn:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

.stock-detail__tab-body {
  background: var(--surface-card);
  padding: var(--space-4);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  min-height: 200px;
  /* UX W8C — 재무 표 7컬럼 모바일 가로 스크롤 활성. */
  overflow-x: auto;
}

/* Tables · lists */
.finance-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
.finance-table th,
.finance-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  text-align: right;
}
.finance-table th:first-child,
.finance-table td:first-child { text-align: left; }
.finance-table th {
  background: var(--surface-muted);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.news-list { list-style: none; padding: 0; margin: 0; }
.news-list li {
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-subtle);
  display: flex; flex-direction: column; gap: var(--space-1);
}
.news-list a {
  color: var(--text-link); text-decoration: none;
  font-size: var(--text-base);
}
.news-list a:hover { text-decoration: underline; }
.news-list small { font-size: var(--text-xs); color: var(--text-tertiary); }

.empty-state {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-secondary);
}
.empty-state i { font-size: 2rem; color: var(--text-tertiary); display: block; margin-bottom: var(--space-2); }
.empty-state small { color: var(--text-tertiary); font-size: var(--text-xs); display: block; margin-top: var(--space-2); }

.stock-detail__retry {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border: 0; border-radius: var(--radius-md);
  font-size: var(--text-sm); cursor: pointer;
}

.stock-detail__footer {
  margin-top: var(--space-8);
  padding: var(--space-4) 0;
  text-align: center;
}
.stock-detail__footer small {
  font-size: var(--text-xs); color: var(--text-tertiary);
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* UX W8C — 모바일 격차 메움 (recon §4 — table 가로 스크롤은 .tab-body 에 적용). */
@media (max-width: 768px) {
  .stock-detail { padding: var(--space-3); }
  .stock-detail__header { padding: var(--space-4) 0 var(--space-3); }
  .stock-detail__name { font-size: var(--text-2xl); }
  .stock-detail__price { font-size: var(--text-3xl); }
  .stock-detail__price-row { flex-wrap: wrap; gap: var(--space-2); }
  .stock-detail__score { margin-left: 0; }
  .stock-detail__chart { padding: var(--space-3); }
  .chart-skeleton, .chart-placeholder, .chart-error { height: 300px; }
  .tab-btn { padding: var(--space-2) var(--space-3); font-size: var(--text-sm); }
  .stock-detail__tab-body { padding: var(--space-3); }
  .finance-table th, .finance-table td { padding: var(--space-1) var(--space-2); font-size: var(--text-xs); white-space: nowrap; }
}
</style>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { chartApi, financeApi, stocksApi, type CandleItem, type FinanceLatest, type StockHistoryItem } from '../api'
import { createChart, CandlestickSeries, LineSeries } from 'lightweight-charts'

const route = useRoute()
const router = useRouter()
const ticker = route.params.ticker as string

// ── State ────────────────────────────────────────────────────────────────
const stockName = ref('')
const stockSector = ref('')
const latestScore = ref<number | null>(null)
const latestTier = ref('')

const chartPeriod = ref('1y')
const candleData = ref<CandleItem[]>([])
const chartLoading = ref(true)

const finance = ref<FinanceLatest | null>(null)
const financeLoading = ref(true)

const scoreHistory = ref<StockHistoryItem[]>([])
const historyLoading = ref(true)

const activeSection = ref<'chart' | 'finance' | 'score'>('chart')

const chartEl = ref<HTMLElement | null>(null)
let chartInstance: ReturnType<typeof createChart> | null = null

const periods = ['1m', '3m', '6m', '1y', '3y', 'all']

// ── Chart ────────────────────────────────────────────────────────────────
async function loadChart() {
  chartLoading.value = true
  try {
    const { data } = await chartApi.get(ticker, chartPeriod.value)
    candleData.value = data.items
    stockName.value = data.name ?? ticker
    await nextTick()
    renderChart()
  } catch {
    candleData.value = []
  } finally {
    chartLoading.value = false
  }
}

function renderChart() {
  if (!chartEl.value || !candleData.value.length) return

  if (chartInstance) {
    chartInstance.remove()
    chartInstance = null
  }

  const chart = createChart(chartEl.value, {
    width: chartEl.value.clientWidth,
    height: 260,
    layout: {
      background: { color: '#ffffff' },
      textColor: '#8C98A7',
    },
    grid: {
      vertLines: { color: '#F5F6F8' },
      horzLines: { color: '#F5F6F8' },
    },
    rightPriceScale: { borderColor: '#E5E8EB' },
    timeScale: {
      borderColor: '#E5E8EB',
      timeVisible: true,
    },
  })

  const candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: '#F03E4C',
    downColor: '#097DF3',
    borderUpColor: '#F03E4C',
    borderDownColor: '#097DF3',
    wickUpColor: '#F03E4C',
    wickDownColor: '#097DF3',
  })

  const formatted = candleData.value.map(c => ({
    time: c.date as any,
    open: c.open ?? 0,
    high: c.high ?? 0,
    low: c.low ?? 0,
    close: c.close ?? 0,
  }))
  candleSeries.setData(formatted)

  // MA20
  const hasMA20 = candleData.value.some(c => c.ma20 != null)
  if (hasMA20) {
    const ma20Series = chart.addSeries(LineSeries, {
      color: '#FF7A00',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    ma20Series.setData(
      candleData.value
        .filter(c => c.ma20 != null)
        .map(c => ({ time: c.date as any, value: c.ma20! }))
    )
  }

  // MA60
  const hasMA60 = candleData.value.some(c => c.ma60 != null)
  if (hasMA60) {
    const ma60Series = chart.addSeries(LineSeries, {
      color: '#5B6DFF',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    ma60Series.setData(
      candleData.value
        .filter(c => c.ma60 != null)
        .map(c => ({ time: c.date as any, value: c.ma60! }))
    )
  }

  chart.timeScale().fitContent()
  chartInstance = chart

  window.addEventListener('resize', () => {
    if (chartEl.value && chartInstance) {
      chartInstance.applyOptions({ width: chartEl.value.clientWidth })
    }
  }, { once: false })
}

// ── Finance ──────────────────────────────────────────────────────────────
async function loadFinance() {
  financeLoading.value = true
  try {
    const { data } = await financeApi.getLatest(ticker)
    finance.value = data
    if (!stockName.value && data.name) stockName.value = data.name
  } catch {
    finance.value = null
  } finally {
    financeLoading.value = false
  }
}

// ── Score history ─────────────────────────────────────────────────────────
async function loadHistory() {
  historyLoading.value = true
  try {
    const { data } = await stocksApi.history(ticker)
    scoreHistory.value = data.items.slice(-30)
    if (data.items.length) {
      const last = data.items[data.items.length - 1]
      latestScore.value = last.score
      latestTier.value = last.tier
    }
  } catch {
    scoreHistory.value = []
  } finally {
    historyLoading.value = false
  }
}

watch(chartPeriod, loadChart)
watch(activeSection, async (val) => {
  if (val === 'chart') {
    await nextTick()
    renderChart()
  }
})

function formatNum(v?: number | null, dec = 1) {
  if (v == null) return '—'
  return v.toFixed(dec)
}

function formatBillion(v?: number | null) {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e12) return (v / 1e12).toFixed(1) + '조'
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(0) + '억'
  return v.toLocaleString()
}

const maxHistoryScore = computed(() => Math.max(...scoreHistory.value.map(s => s.score), 1))
function barHeight(score: number) {
  return Math.round((score / maxHistoryScore.value) * 64) + 'px'
}

import { computed } from 'vue'

onMounted(async () => {
  await Promise.all([loadChart(), loadFinance(), loadHistory()])
})
</script>

<template>
  <div>
    <!-- Header -->
    <div class="stock-detail-header">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
        <button style="color:rgba(255,255,255,.7); font-size:14px;" @click="router.back()">← 뒤로</button>
        <button
          style="color:rgba(255,255,255,.7); font-size:13px; border:1px solid rgba(255,255,255,.3); padding:5px 12px; border-radius:20px;"
          @click="router.push(`/compare?tickers=${ticker}`)"
        >비교 추가</button>
      </div>
      <p class="stock-detail-header__ticker">{{ ticker }}</p>
      <p class="stock-detail-header__name">{{ stockName || '로딩 중...' }}</p>
      <div class="stock-detail-header__badges" v-if="latestScore != null">
        <span class="badge badge--score">{{ Math.round(latestScore) }}점</span>
        <span class="badge badge--tier">{{ latestTier }} 티어</span>
        <span v-if="stockSector" class="badge" style="background:rgba(255,255,255,.15); color:#fff;">{{ stockSector }}</span>
      </div>
    </div>

    <!-- Section tabs -->
    <div style="background:var(--color-card); display:flex; border-bottom:1px solid var(--color-border); position:sticky; top:0; z-index:40;">
      <button class="tab-btn" :class="{ active: activeSection === 'chart' }" @click="activeSection = 'chart'">📊 차트</button>
      <button class="tab-btn" :class="{ active: activeSection === 'finance' }" @click="activeSection = 'finance'">💰 재무</button>
      <button class="tab-btn" :class="{ active: activeSection === 'score' }" @click="activeSection = 'score'">🤖 AI점수</button>
    </div>

    <!-- CHART SECTION -->
    <div v-show="activeSection === 'chart'">
      <div class="chart-container">
        <!-- Period tabs -->
        <div class="chart-periods">
          <button
            v-for="p in periods"
            :key="p"
            class="chart-period-btn"
            :class="{ active: chartPeriod === p }"
            @click="chartPeriod = p"
          >{{ p }}</button>
        </div>

        <!-- MA legend -->
        <div style="display:flex; gap:12px; padding:8px 14px 0; font-size:11px;">
          <span style="display:flex; align-items:center; gap:4px;">
            <span style="width:20px; height:2px; background:#FF7A00; display:inline-block; border-radius:1px;"></span> MA20
          </span>
          <span style="display:flex; align-items:center; gap:4px;">
            <span style="width:20px; height:2px; background:#5B6DFF; display:inline-block; border-radius:1px;"></span> MA60
          </span>
          <span style="display:flex; align-items:center; gap:4px;">
            <span style="width:10px; height:10px; background:#F03E4C; display:inline-block; border-radius:2px;"></span> 상승
          </span>
          <span style="display:flex; align-items:center; gap:4px;">
            <span style="width:10px; height:10px; background:#097DF3; display:inline-block; border-radius:2px;"></span> 하락
          </span>
        </div>

        <div v-if="chartLoading" class="loading-spinner"><div class="spinner"></div></div>
        <div v-else-if="!candleData.length" class="empty-state" style="padding:20px;">
          <span>차트 데이터가 없습니다.</span>
        </div>
        <div v-else ref="chartEl" class="chart-area" style="padding:0;"></div>
      </div>

      <!-- Volume info -->
      <div v-if="candleData.length" style="padding:0 16px 16px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
        <div class="card" style="padding:12px; text-align:center;">
          <p style="font-size:11px; color:var(--color-text-muted);">최근 종가</p>
          <p style="font-size:16px; font-weight:700; margin-top:4px;">
            {{ candleData[candleData.length-1]?.close?.toLocaleString() ?? '—' }}
          </p>
        </div>
        <div class="card" style="padding:12px; text-align:center;">
          <p style="font-size:11px; color:var(--color-text-muted);">거래량</p>
          <p style="font-size:16px; font-weight:700; margin-top:4px;">
            {{ formatBillion(candleData[candleData.length-1]?.volume) }}
          </p>
        </div>
        <div class="card" style="padding:12px; text-align:center;">
          <p style="font-size:11px; color:var(--color-text-muted);">시가총액</p>
          <p style="font-size:16px; font-weight:700; margin-top:4px;">
            {{ formatBillion(candleData[candleData.length-1]?.market_cap) }}
          </p>
        </div>
      </div>
    </div>

    <!-- FINANCE SECTION -->
    <div v-show="activeSection === 'finance'">
      <div v-if="financeLoading" class="loading-spinner"><div class="spinner"></div></div>
      <div v-else-if="!finance" class="empty-state">
        <span class="empty-state__icon">📊</span>
        <span>재무 데이터가 없습니다.</span>
      </div>
      <div v-else>
        <!-- Finance score big card -->
        <div style="margin:12px 16px; padding:20px; background:linear-gradient(135deg,#161C40,#2D3580); border-radius:var(--radius-lg); color:#fff;">
          <p style="font-size:12px; color:rgba(255,255,255,.6); margin-bottom:6px;">
            {{ finance.year }}년 {{ finance.quarter }}분기 재무 스코어
          </p>
          <p style="font-size:42px; font-weight:900; line-height:1;">{{ formatNum(finance.finance_score, 1) }}</p>
          <p style="font-size:14px; color:rgba(255,255,255,.7);">/ 100점</p>
          <div class="score-bar" style="margin-top:12px; height:8px;">
            <div class="score-bar__fill" :style="{ width: (finance.finance_score ?? 0) + '%' }"></div>
          </div>
        </div>

        <!-- Grid metrics -->
        <div class="finance-grid">
          <div class="finance-metric-card">
            <p class="finance-metric-card__label">PER</p>
            <p class="finance-metric-card__value">{{ formatNum(finance.per) }}</p>
            <p class="finance-metric-card__sub">주가수익비율</p>
          </div>
          <div class="finance-metric-card">
            <p class="finance-metric-card__label">PBR</p>
            <p class="finance-metric-card__value">{{ formatNum(finance.pbr) }}</p>
            <p class="finance-metric-card__sub">주가순자산비율</p>
          </div>
          <div class="finance-metric-card">
            <p class="finance-metric-card__label">ROE</p>
            <p class="finance-metric-card__value" :class="(finance.roe ?? 0) >= 0 ? 'up' : 'down'">
              {{ formatNum(finance.roe) }}%
            </p>
            <p class="finance-metric-card__sub">자기자본이익률</p>
          </div>
          <div class="finance-metric-card">
            <p class="finance-metric-card__label">부채비율</p>
            <p class="finance-metric-card__value" :class="(finance.debt_ratio ?? 0) > 150 ? 'down' : ''">
              {{ formatNum(finance.debt_ratio) }}%
            </p>
            <p class="finance-metric-card__sub">안전성 지표</p>
          </div>
          <div class="finance-metric-card">
            <p class="finance-metric-card__label">영업이익률</p>
            <p class="finance-metric-card__value" :class="(finance.op_margin ?? 0) >= 0 ? 'up' : 'down'">
              {{ formatNum(finance.op_margin) }}%
            </p>
            <p class="finance-metric-card__sub">수익성 지표</p>
          </div>
          <div class="finance-metric-card">
            <p class="finance-metric-card__label">매출성장률 YoY</p>
            <p class="finance-metric-card__value" :class="(finance.rev_growth_yoy ?? 0) >= 0 ? 'up' : 'down'">
              {{ formatNum(finance.rev_growth_yoy) }}%
            </p>
            <p class="finance-metric-card__sub">성장성 지표</p>
          </div>
          <div class="finance-metric-card">
            <p class="finance-metric-card__label">순이익</p>
            <p class="finance-metric-card__value">{{ formatBillion(finance.net_profit) }}</p>
            <p class="finance-metric-card__sub">원</p>
          </div>
          <div class="finance-metric-card">
            <p class="finance-metric-card__label">매출액</p>
            <p class="finance-metric-card__value">{{ formatBillion(finance.revenue) }}</p>
            <p class="finance-metric-card__sub">원</p>
          </div>
        </div>
      </div>
    </div>

    <!-- SCORE SECTION -->
    <div v-show="activeSection === 'score'">
      <div v-if="historyLoading" class="loading-spinner"><div class="spinner"></div></div>
      <div v-else-if="!scoreHistory.length" class="empty-state">
        <span class="empty-state__icon">🤖</span>
        <span>AI 점수 이력이 없습니다.</span>
      </div>
      <div v-else>
        <!-- Current score big -->
        <div style="margin:12px 16px; padding:20px; background:var(--color-card); border-radius:var(--radius-lg); box-shadow:var(--shadow-md);">
          <p style="font-size:13px; color:var(--color-text-sub); margin-bottom:8px;">최신 AI ML 점수</p>
          <div style="display:flex; align-items:baseline; gap:8px;">
            <span style="font-size:52px; font-weight:900; color:var(--color-accent); line-height:1;">{{ Math.round(latestScore ?? 0) }}</span>
            <span style="font-size:18px; color:var(--color-text-muted);">/ 100</span>
            <span class="tier-badge" :class="latestTier" style="width:28px; height:28px; font-size:14px;">{{ latestTier }}</span>
          </div>
          <div class="score-bar" style="margin-top:12px; height:8px;">
            <div class="score-bar__fill" :style="{ width: (latestScore ?? 0) + '%' }"></div>
          </div>
          <p style="font-size:12px; color:var(--color-text-muted); margin-top:8px;">
            80점 이상: A티어 · 60~79: B티어 · 40~59: C티어 · 40 미만: D티어
          </p>
        </div>

        <!-- Score history bar chart -->
        <div class="score-history">
          <p class="score-history__title">점수 이력 (최근 {{ scoreHistory.length }}일)</p>
          <div class="score-history__chart">
            <div
              v-for="(h, i) in scoreHistory"
              :key="i"
              class="score-bar-item"
              :class="{ highlight: h.tier === 'A' }"
              :style="{ height: barHeight(h.score) }"
              :title="`${h.date}: ${Math.round(h.score)}점 (${h.tier})`"
            ></div>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--color-text-muted); margin-top:4px;">
            <span>{{ scoreHistory[0]?.date }}</span>
            <span>{{ scoreHistory[scoreHistory.length - 1]?.date }}</span>
          </div>
        </div>

        <!-- Score table (recent 10) -->
        <div style="margin:0 16px 16px; background:var(--color-card); border-radius:var(--radius-md); overflow:hidden; box-shadow:var(--shadow-sm);">
          <table style="width:100%; border-collapse:collapse;">
            <thead>
              <tr style="background:var(--color-primary);">
                <th style="color:#fff; padding:10px 14px; font-size:12px; text-align:left;">날짜</th>
                <th style="color:#fff; padding:10px 14px; font-size:12px; text-align:right;">점수</th>
                <th style="color:#fff; padding:10px 14px; font-size:12px; text-align:right;">티어</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="h in [...scoreHistory].reverse().slice(0, 10)"
                :key="h.date"
                style="border-bottom:1px solid var(--color-border);"
              >
                <td style="padding:10px 14px; font-size:13px; color:var(--color-text-sub);">{{ h.date }}</td>
                <td style="padding:10px 14px; font-size:13px; font-weight:700; text-align:right; color:var(--color-accent);">
                  {{ Math.round(h.score) }}점
                </td>
                <td style="padding:10px 14px; text-align:right;">
                  <span class="tier-badge" :class="h.tier">{{ h.tier }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

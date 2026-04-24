<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { compareApi, stocksApi, type CompareItem, type SearchResult } from '../api'

const route = useRoute()
const router = useRouter()

const tickers = ref<string[]>([])
const searchQ = ref('')
const searchResults = ref<SearchResult[]>([])
const showSearch = ref(false)
const compareData = ref<CompareItem[]>([])
const loading = ref(false)
const error = ref('')

let searchTimer: ReturnType<typeof setTimeout>

function onSearchInput() {
  clearTimeout(searchTimer)
  if (!searchQ.value.trim()) {
    searchResults.value = []
    showSearch.value = false
    return
  }
  showSearch.value = true
  searchTimer = setTimeout(async () => {
    try {
      const { data } = await stocksApi.search(searchQ.value.trim(), 8)
      searchResults.value = data.items
    } catch {
      searchResults.value = []
    }
  }, 300)
}

function addTicker(ticker: string) {
  if (tickers.value.length >= 5) return
  if (!tickers.value.includes(ticker)) {
    tickers.value.push(ticker)
  }
  showSearch.value = false
  searchQ.value = ''
  searchResults.value = []
}

function removeTicker(ticker: string) {
  tickers.value = tickers.value.filter(t => t !== ticker)
  compareData.value = compareData.value.filter(c => c.ticker !== ticker)
}

async function runCompare() {
  if (!tickers.value.length) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await compareApi.compare(tickers.value, '1y')
    compareData.value = data.items
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? '비교 데이터를 불러올 수 없습니다.'
  } finally {
    loading.value = false
  }
}

function formatNum(v?: number | null, dec = 1) {
  if (v == null) return '—'
  return v.toFixed(dec)
}

const financeMetrics = [
  { key: 'finance_score', label: '재무 스코어' },
  { key: 'roe', label: 'ROE (%)' },
  { key: 'per', label: 'PER' },
  { key: 'pbr', label: 'PBR' },
  { key: 'debt_ratio', label: '부채비율 (%)' },
  { key: 'op_margin', label: '영업이익률 (%)' },
  { key: 'rev_growth_yoy', label: '매출성장률 (%)' },
]

onMounted(() => {
  const q = route.query.tickers as string
  if (q) {
    tickers.value = q.split(',').filter(Boolean).slice(0, 5)
    runCompare()
  }
})
</script>

<template>
  <div>
    <!-- Header -->
    <header class="app-header">
      <button class="app-header__btn" @click="router.back()">← 뒤로</button>
      <span style="color:#fff; font-size:17px; font-weight:700;">종목 비교</span>
      <div style="width:60px;"></div>
    </header>

    <!-- Input area -->
    <div class="compare-header">
      <div class="compare-input-wrap">
        <span v-for="t in tickers" :key="t" class="compare-tag">
          {{ t }}
          <button class="compare-tag__remove" @click="removeTicker(t)">✕</button>
        </span>
        <button
          v-if="tickers.length < 5"
          class="compare-add-btn"
          @click="showSearch = !showSearch"
        >+ 종목 추가</button>
      </div>

      <!-- Search box -->
      <div v-if="showSearch" style="margin-top:12px; position:relative;">
        <div class="search-box" style="background:var(--color-bg); border-color:var(--color-border);">
          <span class="search-box__icon" style="color:var(--color-text-sub);">🔍</span>
          <input
            v-model="searchQ"
            class="search-box__input"
            style="color:var(--color-text);"
            placeholder="종목명 또는 코드"
            @input="onSearchInput"
            autofocus
          />
        </div>
        <div v-if="searchResults.length" class="search-dropdown" style="top:calc(100% + 4px);">
          <div
            v-for="item in searchResults"
            :key="item.ticker"
            class="search-item"
            @mousedown.prevent="addTicker(item.ticker)"
          >
            <span class="search-item__ticker">{{ item.ticker }}</span>
            <span class="search-item__name">{{ item.name ?? item.ticker }}</span>
            <span v-if="item.tier" class="tier-badge" :class="item.tier">{{ item.tier }}</span>
          </div>
        </div>
      </div>

      <button
        v-if="tickers.length >= 2"
        @click="runCompare"
        style="width:100%; margin-top:12px; padding:12px; background:var(--color-accent); color:#fff;
               border-radius:var(--radius-xl); font-size:14px; font-weight:700;"
      >
        비교 분석 시작
      </button>
      <p v-else style="margin-top:8px; font-size:13px; color:var(--color-text-muted);">
        종목을 2개 이상 추가하세요 (최대 5개)
      </p>
    </div>

    <div v-if="loading" class="loading-spinner"><div class="spinner"></div></div>

    <div v-else-if="error" class="empty-state">
      <span class="empty-state__icon">⚠️</span>
      <span>{{ error }}</span>
    </div>

    <div v-else-if="compareData.length">
      <!-- Score comparison cards -->
      <div style="padding:16px; display:flex; gap:10px; overflow-x:auto; scrollbar-width:none;">
        <div
          v-for="item in compareData"
          :key="item.ticker"
          class="card"
          style="flex-shrink:0; min-width:140px; padding:16px; text-align:center; cursor:pointer;"
          @click="router.push(`/stock/${item.ticker}`)"
        >
          <div class="tier-badge" :class="item.latest_tier" style="margin:0 auto 8px; width:32px; height:32px; font-size:16px;">
            {{ item.latest_tier }}
          </div>
          <p style="font-size:13px; font-weight:700; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
            {{ item.name ?? item.ticker }}
          </p>
          <p style="font-size:11px; color:var(--color-text-muted); margin-bottom:10px;">{{ item.ticker }}</p>
          <p style="font-size:32px; font-weight:900; color:var(--color-accent); line-height:1;">
            {{ Math.round(item.latest_score ?? 0) }}
          </p>
          <p style="font-size:11px; color:var(--color-text-muted);">ML 점수</p>
          <div class="score-bar" style="margin-top:8px;">
            <div class="score-bar__fill" :style="{ width: (item.latest_score ?? 0) + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Finance comparison table -->
      <div class="section-header">
        <h2>재무 비교</h2>
      </div>
      <div class="compare-table">
        <table>
          <thead>
            <tr>
              <th>지표</th>
              <th v-for="item in compareData" :key="item.ticker">{{ item.name?.slice(0,4) ?? item.ticker }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in financeMetrics" :key="m.key">
              <td>{{ m.label }}</td>
              <td
                v-for="item in compareData"
                :key="item.ticker"
                style="font-weight:600; text-align:right;"
              >
                {{ formatNum((item.finance as any)?.[m.key]) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Score history comparison (mini bars) -->
      <div class="section-header"><h2>점수 이력</h2></div>
      <div style="padding:0 16px 16px;">
        <div
          v-for="item in compareData"
          :key="item.ticker"
          class="card"
          style="padding:14px; margin-bottom:10px;"
        >
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <p style="font-size:14px; font-weight:700;">{{ item.name ?? item.ticker }}</p>
            <span class="tier-badge" :class="item.latest_tier">{{ item.latest_tier }}</span>
          </div>
          <div style="display:flex; align-items:flex-end; gap:2px; height:48px;" v-if="item.score_history?.length">
            <div
              v-for="(h, i) in item.score_history?.slice(-30)"
              :key="i"
              :style="{
                flex: '1',
                height: Math.round((h.score / 100) * 44) + 'px',
                background: h.tier === 'A' ? 'var(--color-accent)' : 'var(--color-accent-lt)',
                borderRadius: '2px 2px 0 0',
                minHeight: '3px',
              }"
              :title="`${h.date}: ${Math.round(h.score)}점`"
            ></div>
          </div>
          <p v-else style="font-size:12px; color:var(--color-text-muted);">이력 없음</p>
        </div>
      </div>
    </div>

    <div v-else-if="tickers.length && !loading" class="empty-state">
      <span class="empty-state__icon">⚖️</span>
      <span>비교 버튼을 눌러 분석을 시작하세요.</span>
    </div>
  </div>
</template>

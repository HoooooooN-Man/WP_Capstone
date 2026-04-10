<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { stocksApi, type StockScore } from '../api'

const router = useRouter()

const stocks = ref<StockScore[]>([])
const loading = ref(true)
const error = ref('')
const selectedDate = ref('')
const availableDates = ref<string[]>([])
const activeTab = ref<string>('all')
const sortBy = ref<'score' | 'name'>('score')

async function loadDates() {
  try {
    const { data } = await stocksApi.dates()
    availableDates.value = (data as any).dates ?? []
    selectedDate.value = (data as any).latest ?? ''
  } catch {
    availableDates.value = []
  }
}

async function loadStocks() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { top_k: 0 }
    if (selectedDate.value) params.date = selectedDate.value
    const { data } = await stocksApi.recommendations(params)
    stocks.value = data.items
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? '데이터를 불러올 수 없습니다.'
    stocks.value = []
  } finally {
    loading.value = false
  }
}

watch(selectedDate, loadStocks)

const tiers = ['all', 'A', 'B', 'C', 'D']

const filteredStocks = computed(() => {
  let list = activeTab.value === 'all'
    ? stocks.value
    : stocks.value.filter(s => s.tier === activeTab.value)

  if (sortBy.value === 'name') {
    return [...list].sort((a, b) => (a.name ?? a.ticker).localeCompare(b.name ?? b.ticker))
  }
  return list
})

const tierCounts = computed(() => {
  const counts: Record<string, number> = { all: stocks.value.length }
  for (const t of ['A', 'B', 'C', 'D']) {
    counts[t] = stocks.value.filter(s => s.tier === t).length
  }
  return counts
})

function scoreWidth(score: number) {
  return `${Math.round(score)}%`
}

onMounted(async () => {
  await loadDates()
  await loadStocks()
})
</script>

<template>
  <div>
    <!-- Header -->
    <header class="app-header">
      <button class="app-header__btn" @click="router.back()">← 뒤로</button>
      <span style="color:#fff; font-size:17px; font-weight:700;">AI 추천 종목</span>
      <div style="width:60px;"></div>
    </header>

    <!-- Date selector -->
    <div style="padding:12px 16px; background:var(--color-primary);">
      <select
        v-model="selectedDate"
        style="background:rgba(255,255,255,.12); border:1.5px solid rgba(255,255,255,.25); color:#fff;
               padding:8px 14px; border-radius:20px; font-size:13px; outline:none; width:100%;
               font-family:inherit;"
      >
        <option v-for="d in availableDates" :key="d" :value="d" style="background:#fff; color:#24282C;">
          {{ d }}
        </option>
      </select>
    </div>

    <!-- Tier tabs -->
    <div style="background:var(--color-card); position:sticky; top:56px; z-index:40;">
      <div style="display:flex; border-bottom:1px solid var(--color-border); overflow-x:auto; scrollbar-width:none;">
        <button
          v-for="tier in tiers"
          :key="tier"
          class="tab-btn"
          style="flex-shrink:0;"
          :class="{ active: activeTab === tier }"
          @click="activeTab = tier"
        >
          {{ tier === 'all' ? '전체' : tier + '티어' }}
          <span style="font-size:11px; color:var(--color-text-muted); margin-left:2px;">
            ({{ tierCounts[tier] }})
          </span>
        </button>
      </div>
    </div>

    <!-- Sort + count bar -->
    <div class="screener-result-bar">
      <span class="screener-result-count">
        총 <span>{{ filteredStocks.length }}</span>개 종목
      </span>
      <select v-model="sortBy" class="sort-select">
        <option value="score">점수순</option>
        <option value="name">이름순</option>
      </select>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-spinner"><div class="spinner"></div></div>

    <!-- Error -->
    <div v-else-if="error" class="empty-state">
      <span class="empty-state__icon">⚠️</span>
      <span>{{ error }}</span>
    </div>

    <!-- Stock list -->
    <div v-else-if="filteredStocks.length" class="stock-list">
      <div
        v-for="(stock, i) in filteredStocks"
        :key="stock.ticker"
        class="stock-item"
        @click="router.push(`/stock/${stock.ticker}`)"
      >
        <span class="stock-item__rank">{{ i + 1 }}</span>
        <div class="stock-item__logo">
          {{ stock.name?.[0] ?? stock.ticker[0] }}
        </div>
        <div class="stock-item__info">
          <p class="stock-item__name">{{ stock.name ?? stock.ticker }}</p>
          <div class="stock-item__meta">
            <span class="stock-item__ticker">{{ stock.ticker }}</span>
            <span class="stock-item__sector" v-if="stock.sector">· {{ stock.sector }}</span>
          </div>
          <div class="score-bar" style="width:80px; margin-top:4px;">
            <div class="score-bar__fill" :style="{ width: scoreWidth(stock.score) }"></div>
          </div>
        </div>
        <div class="stock-item__right">
          <p class="stock-item__score-num">{{ Math.round(stock.score) }}</p>
          <p class="stock-item__score-label">점</p>
        </div>
        <span class="tier-badge" :class="stock.tier">{{ stock.tier }}</span>
      </div>
    </div>

    <div v-else class="empty-state">
      <span class="empty-state__icon">📭</span>
      <span>해당 티어 데이터가 없습니다.</span>
    </div>
  </div>
</template>

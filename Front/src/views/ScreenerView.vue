<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { screenerApi, type ScreenerItem } from '../api'

const router = useRouter()
const route = useRoute()

// ── Filter state ─────────────────────────────────────────────────────────
const tier = ref('')
const sector = ref((route.query.sector as string) ?? '')
const minScore = ref(0)
const maxPer = ref<number | ''>('')
const maxPbr = ref<number | ''>('')
const minRoe = ref<number | ''>('')
const maxDebtRatio = ref<number | ''>('')
const minOpMargin = ref<number | ''>('')
const sortBy = ref('composite_score')

const results = ref<ScreenerItem[]>([])
const loading = ref(false)
const searched = ref(false)

const tierOptions = ['', 'A', 'B', 'C', 'D']
const sortOptions = [
  { value: 'composite_score', label: '복합 스코어' },
  { value: 'score', label: 'ML 점수' },
  { value: 'finance_score', label: '재무 스코어' },
  { value: 'roe', label: 'ROE' },
]

async function runScreener() {
  loading.value = true
  searched.value = true
  try {
    const params: Record<string, unknown> = {
      sort_by: sortBy.value,
      limit: 100,
    }
    if (tier.value) params.tier = tier.value
    if (sector.value) params.sector = sector.value
    if (minScore.value > 0) params.min_score = minScore.value
    if (maxPer.value !== '') params.max_per = maxPer.value
    if (maxPbr.value !== '') params.max_pbr = maxPbr.value
    if (minRoe.value !== '') params.min_roe = minRoe.value
    if (maxDebtRatio.value !== '') params.max_debt_ratio = maxDebtRatio.value
    if (minOpMargin.value !== '') params.min_op_margin = minOpMargin.value

    const { data } = await screenerApi.screen(params)
    results.value = data.items
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  tier.value = ''
  sector.value = ''
  minScore.value = 0
  maxPer.value = ''
  maxPbr.value = ''
  minRoe.value = ''
  maxDebtRatio.value = ''
  minOpMargin.value = ''
  sortBy.value = 'composite_score'
}

function scoreWidth(score?: number) {
  return `${Math.round(score ?? 0)}%`
}

function formatNum(v?: number, dec = 1) {
  if (v == null) return '—'
  return v.toFixed(dec)
}

onMounted(() => {
  if (route.query.sector) runScreener()
})
</script>

<template>
  <div>
    <!-- Header -->
    <header class="app-header">
      <button class="app-header__btn" @click="router.back()">← 뒤로</button>
      <span style="color:#fff; font-size:17px; font-weight:700;">종목 스크리너</span>
      <button class="app-header__btn" @click="resetFilters">초기화</button>
    </header>

    <!-- Filter panel -->
    <div class="screener-filter">
      <!-- Tier -->
      <div class="filter-group">
        <p class="filter-label">티어</p>
        <div class="filter-chips">
          <button
            v-for="t in tierOptions"
            :key="t"
            class="filter-chip"
            :class="{ active: tier === t }"
            @click="tier = t"
          >{{ t === '' ? '전체' : t + '티어' }}</button>
        </div>
      </div>

      <!-- ML Score min -->
      <div class="filter-group">
        <p class="filter-label">최소 ML 점수: <strong>{{ minScore }}점</strong></p>
        <input
          v-model.number="minScore"
          type="range" min="0" max="100" step="5"
          style="width:100%; accent-color:var(--color-accent);"
        />
        <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--color-text-muted);">
          <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
        </div>
      </div>

      <!-- Sector -->
      <div class="filter-group">
        <p class="filter-label">섹터 (키워드)</p>
        <input v-model="sector" class="filter-input" placeholder="예: IT, 금융, 의약품" />
      </div>

      <!-- Financial filters -->
      <div class="filter-group">
        <p class="filter-label">재무 조건</p>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
          <div>
            <p style="font-size:11px; color:var(--color-text-muted); margin-bottom:4px;">최대 PER</p>
            <input v-model.number="maxPer" class="filter-input" type="number" placeholder="예: 30" />
          </div>
          <div>
            <p style="font-size:11px; color:var(--color-text-muted); margin-bottom:4px;">최대 PBR</p>
            <input v-model.number="maxPbr" class="filter-input" type="number" placeholder="예: 3" />
          </div>
          <div>
            <p style="font-size:11px; color:var(--color-text-muted); margin-bottom:4px;">최소 ROE (%)</p>
            <input v-model.number="minRoe" class="filter-input" type="number" placeholder="예: 10" />
          </div>
          <div>
            <p style="font-size:11px; color:var(--color-text-muted); margin-bottom:4px;">최대 부채비율 (%)</p>
            <input v-model.number="maxDebtRatio" class="filter-input" type="number" placeholder="예: 100" />
          </div>
          <div>
            <p style="font-size:11px; color:var(--color-text-muted); margin-bottom:4px;">최소 영업이익률 (%)</p>
            <input v-model.number="minOpMargin" class="filter-input" type="number" placeholder="예: 5" />
          </div>
        </div>
      </div>

      <!-- Sort -->
      <div class="filter-group">
        <p class="filter-label">정렬 기준</p>
        <div class="filter-chips">
          <button
            v-for="opt in sortOptions"
            :key="opt.value"
            class="filter-chip"
            :class="{ active: sortBy === opt.value }"
            @click="sortBy = opt.value"
          >{{ opt.label }}</button>
        </div>
      </div>

      <button
        @click="runScreener"
        style="width:100%; padding:14px; background:var(--color-accent); color:#fff;
               border-radius:var(--radius-xl); font-size:15px; font-weight:700; margin-top:4px;"
      >
        🔍 검색하기
      </button>
    </div>

    <!-- Results bar -->
    <div v-if="searched" class="screener-result-bar">
      <span class="screener-result-count">
        총 <span>{{ results.length }}</span>개 종목
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-spinner"><div class="spinner"></div></div>

    <!-- Results -->
    <div v-else-if="results.length" class="stock-list">
      <div
        v-for="(item, i) in results"
        :key="item.ticker"
        class="stock-item"
        @click="router.push(`/stock/${item.ticker}`)"
      >
        <span class="stock-item__rank">{{ i + 1 }}</span>
        <div class="stock-item__logo">{{ item.name?.[0] ?? item.ticker[0] }}</div>
        <div class="stock-item__info">
          <p class="stock-item__name">{{ item.name ?? item.ticker }}</p>
          <div class="stock-item__meta">
            <span class="stock-item__ticker">{{ item.ticker }}</span>
            <span class="stock-item__sector" v-if="item.sector">· {{ item.sector }}</span>
          </div>
          <!-- Mini metrics -->
          <div style="display:flex; gap:8px; margin-top:4px; font-size:11px; color:var(--color-text-muted);">
            <span v-if="item.roe != null">ROE {{ formatNum(item.roe) }}%</span>
            <span v-if="item.per != null">PER {{ formatNum(item.per) }}</span>
            <span v-if="item.op_margin != null">영업이익률 {{ formatNum(item.op_margin) }}%</span>
          </div>
        </div>
        <div class="stock-item__right">
          <p class="stock-item__score-num" style="font-size:16px;">
            {{ Math.round(item.composite_score ?? item.score ?? 0) }}
          </p>
          <div class="score-bar stock-item__scorebar">
            <div class="score-bar__fill" :style="{ width: scoreWidth(item.composite_score ?? item.score) }"></div>
          </div>
          <p class="stock-item__score-label">복합</p>
        </div>
        <span class="tier-badge" :class="item.tier">{{ item.tier }}</span>
      </div>
    </div>

    <div v-else-if="searched && !loading" class="empty-state">
      <span class="empty-state__icon">🔎</span>
      <span>조건에 맞는 종목이 없습니다.</span>
      <button @click="resetFilters" style="margin-top:8px; color:var(--color-accent); font-size:14px; font-weight:600;">
        필터 초기화
      </button>
    </div>

    <div v-else class="empty-state">
      <span class="empty-state__icon">🔍</span>
      <span>조건을 설정하고 검색하세요.</span>
    </div>
  </div>
</template>

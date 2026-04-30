<template>
  <div class="news-view">
    <!-- 페이지 헤더 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">📰</span>
          뉴스 감성 랭킹
        </h1>
        <p class="page-desc">FinBERT 기반 뉴스 감성 분석 랭킹입니다.</p>
      </div>
      <div class="header-controls">
        <!-- 날짜 선택 -->
        <select v-model="selectedDate" class="date-select" @change="fetchRankings" :disabled="loading">
          <option v-if="!dates.length" value="">날짜 로딩 중...</option>
          <option v-for="date in dates" :key="date" :value="date">{{ date }}</option>
        </select>
      </div>
    </div>

    <!-- 감성 분포 요약 배너 -->
    <div v-if="items.length" class="sentiment-banner">
      <div class="sentiment-stat positive">
        <span class="stat-icon">📈</span>
        <span class="stat-count">{{ sentimentStats.positive }}</span>
        <span class="stat-label">긍정</span>
      </div>
      <div class="sentiment-divider" />
      <div class="sentiment-stat neutral">
        <span class="stat-icon">➖</span>
        <span class="stat-count">{{ sentimentStats.neutral }}</span>
        <span class="stat-label">중립</span>
      </div>
      <div class="sentiment-divider" />
      <div class="sentiment-stat negative">
        <span class="stat-icon">📉</span>
        <span class="stat-count">{{ sentimentStats.negative }}</span>
        <span class="stat-label">부정</span>
      </div>
      <div class="sentiment-divider" />
      <div class="sentiment-stat total">
        <span class="stat-count">{{ items.length }}</span>
        <span class="stat-label">전체 기사</span>
      </div>
    </div>

    <!-- 에러 카드 -->
    <div v-if="error" class="error-card">
      <span class="error-icon">⚠️</span>
      <p>{{ error }}</p>
      <button class="retry-btn" @click="init">재시도</button>
    </div>

    <!-- 로딩 스켈레톤 -->
    <div v-else-if="loading" class="skeleton-list">
      <div v-for="n in 10" :key="n" class="skeleton-item">
        <div class="skeleton-rank" />
        <div class="skeleton-body">
          <div class="skeleton-title" />
          <div class="skeleton-meta" />
        </div>
        <div class="skeleton-badge" />
      </div>
    </div>

    <!-- 503 빈 데이터 -->
    <div v-else-if="!items.length" class="empty-card">
      <span>📭</span>
      <p>해당 날짜의 뉴스 랭킹 데이터가 없습니다.</p>
    </div>

    <!-- 랭킹 리스트 -->
    <div v-else class="ranking-list">
      <a
        v-for="item in items"
        :key="item.news_id"
        :href="item.google_url || item.origin_url || '#'"
        target="_blank"
        rel="noopener noreferrer"
        class="ranking-item"
        :class="[`sentiment-${item.sentiment_label}`, { 'has-image': item.image_url }]"
      >
        <!-- 순위 배지 -->
        <div class="rank-badge" :class="rankClass(item.rank)">
          {{ item.rank }}
        </div>

        <!-- 썸네일 (있을 때만) -->
        <div v-if="item.image_url" class="thumbnail-wrap">
          <img
            :src="item.image_url"
            :alt="item.title"
            class="thumbnail"
            loading="lazy"
            @error="(e) => (e.target.style.display = 'none')"
          />
        </div>

        <!-- 본문 -->
        <div class="item-body">
          <div class="item-meta">
            <span class="source-name">{{ item.source_name || item.provider }}</span>
            <span class="published-at">{{ formatDate(item.published_at) }}</span>
          </div>
          <h3 class="item-title">{{ item.title }}</h3>

          <!-- FinBERT 감성 바 -->
          <div class="sentiment-row">
            <SentimentBadge :label="item.sentiment_label" :score="item.sentiment_score" />
            <div class="prob-bars">
              <div class="prob-bar-wrap" title="긍정">
                <div class="prob-bar pos" :style="{ width: pct(item.pos_prob) }" />
                <span class="prob-label">{{ pct(item.pos_prob) }}</span>
              </div>
              <div class="prob-bar-wrap" title="중립">
                <div class="prob-bar neu" :style="{ width: pct(item.neu_prob) }" />
                <span class="prob-label">{{ pct(item.neu_prob) }}</span>
              </div>
              <div class="prob-bar-wrap" title="부정">
                <div class="prob-bar neg" :style="{ width: pct(item.neg_prob) }" />
                <span class="prob-label">{{ pct(item.neg_prob) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 감성 스코어 -->
        <div class="score-wrap">
          <span class="score-value" :class="`score-${item.sentiment_label}`">
            {{ (item.sentiment_score * 100).toFixed(0) }}
          </span>
          <span class="score-unit">점</span>
        </div>
      </a>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import dbapi from '@/api/dbapi'

// ── 하위 컴포넌트 (인라인 정의) ─────────────────────────────────────────────
// 별도 파일로 분리해도 됩니다. 여기서는 defineComponent로 인라인 사용합니다.
import { defineComponent, h } from 'vue'

const SentimentBadge = defineComponent({
  props: {
    label: { type: String, required: true },
    score: { type: Number, default: 0 },
  },
  setup(props) {
    const config = {
      positive: { text: '긍정', emoji: '📈', cls: 'badge-pos' },
      neutral:  { text: '중립', emoji: '➖', cls: 'badge-neu' },
      negative: { text: '부정', emoji: '📉', cls: 'badge-neg' },
    }
    return () => {
      const c = config[props.label] || config.neutral
      return h(
        'span',
        { class: ['sentiment-badge', c.cls] },
        `${c.emoji} ${c.text}`
      )
    }
  },
})

// ── 상태 ────────────────────────────────────────────────────────────────────
const dates     = ref([])
const selectedDate = ref('')
const items     = ref([])
const loading   = ref(false)
const error     = ref(null)

// ── 계산 ────────────────────────────────────────────────────────────────────
const sentimentStats = computed(() => {
  return items.value.reduce(
    (acc, item) => {
      if (item.sentiment_label === 'positive') acc.positive++
      else if (item.sentiment_label === 'negative') acc.negative++
      else acc.neutral++
      return acc
    },
    { positive: 0, neutral: 0, negative: 0 }
  )
})

// ── 유틸 ────────────────────────────────────────────────────────────────────
function pct(val) {
  if (val == null) return '0%'
  return `${(val * 100).toFixed(0)}%`
}

function formatDate(val) {
  if (!val) return ''
  const d = new Date(val)
  if (isNaN(d)) return val
  return d.toLocaleString('ko-KR', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function rankClass(rank) {
  if (rank === 1) return 'rank-gold'
  if (rank === 2) return 'rank-silver'
  if (rank === 3) return 'rank-bronze'
  return ''
}

// ── API 호출 ─────────────────────────────────────────────────────────────────
async function fetchDates() {
  try {
    const { data } = await dbapi.get('/api/v1/news/rankings/dates')
    dates.value = data.dates || []
    if (data.latest) selectedDate.value = data.latest
  } catch (e) {
    error.value = '날짜 목록을 불러오지 못했습니다.'
  }
}

async function fetchRankings() {
  if (!selectedDate.value) return
  loading.value = true
  error.value = null
  try {
    const { data } = await dbapi.get('/api/v1/news/rankings', {
      params: { display_date: selectedDate.value, limit: 50 },
    })
    items.value = data.items || []
  } catch (e) {
    if (e.response?.status === 503) {
      error.value = '서버 점검 중이거나 DuckDB 데이터가 비어 있습니다.'
    } else {
      error.value = '뉴스 랭킹을 불러오지 못했습니다.'
    }
    items.value = []
  } finally {
    loading.value = false
  }
}

async function init() {
  error.value = null
  await fetchDates()
  await fetchRankings()
}

onMounted(init)
</script>

<style scoped>
/* ── 레이아웃 ─────────────────────────────────────────────────────────────── */
.news-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px 64px;
}

/* ── 헤더 ─────────────────────────────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 24px;
}
.page-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-desc {
  color: #64748b;
  margin: 4px 0 0;
  font-size: 0.875rem;
}
.date-select {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.9rem;
  background: #fff;
  cursor: pointer;
  outline: none;
}
.date-select:focus { border-color: #6366f1; }

/* ── 감성 분포 배너 ───────────────────────────────────────────────────────── */
.sentiment-banner {
  display: flex;
  align-items: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 24px;
  margin-bottom: 24px;
  gap: 0;
}
.sentiment-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  gap: 2px;
}
.stat-icon { font-size: 1.2rem; }
.stat-count {
  font-size: 1.5rem;
  font-weight: 700;
}
.stat-label { font-size: 0.78rem; color: #64748b; }
.sentiment-stat.positive .stat-count { color: #16a34a; }
.sentiment-stat.negative .stat-count { color: #dc2626; }
.sentiment-stat.neutral  .stat-count { color: #64748b; }
.sentiment-stat.total    .stat-count { color: #1e293b; }
.sentiment-divider {
  width: 1px;
  height: 40px;
  background: #e2e8f0;
  margin: 0 8px;
}

/* ── 에러 / 빈 / 스켈레톤 ─────────────────────────────────────────────────── */
.error-card, .empty-card {
  text-align: center;
  padding: 48px;
  background: #fef2f2;
  border-radius: 12px;
  color: #b91c1c;
  font-size: 0.95rem;
}
.empty-card { background: #f8fafc; color: #64748b; font-size: 1.2rem; }
.empty-card span { font-size: 2.5rem; display: block; margin-bottom: 12px; }
.retry-btn {
  margin-top: 16px;
  padding: 8px 20px;
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
}
.retry-btn:hover { background: #dc2626; }

.skeleton-list { display: flex; flex-direction: column; gap: 12px; }
.skeleton-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  animation: pulse 1.4s ease-in-out infinite;
}
.skeleton-rank  { width: 40px; height: 40px; border-radius: 50%;  background: #e2e8f0; flex-shrink: 0; }
.skeleton-body  { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.skeleton-title { height: 18px; background: #e2e8f0; border-radius: 4px; width: 75%; }
.skeleton-meta  { height: 12px; background: #e2e8f0; border-radius: 4px; width: 40%; }
.skeleton-badge { width: 60px; height: 28px; background: #e2e8f0; border-radius: 6px; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ── 랭킹 리스트 ──────────────────────────────────────────────────────────── */
.ranking-list { display: flex; flex-direction: column; gap: 12px; }

.ranking-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.15s, transform 0.15s, border-color 0.15s;
  position: relative;
  overflow: hidden;
}
.ranking-item::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  border-radius: 4px 0 0 4px;
}
.ranking-item.sentiment-positive::before { background: #16a34a; }
.ranking-item.sentiment-negative::before { background: #dc2626; }
.ranking-item.sentiment-neutral::before  { background: #94a3b8; }

.ranking-item:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  transform: translateY(-2px);
  border-color: #c7d2fe;
}

/* FinBERT 배경 틴트 */
.ranking-item.sentiment-positive { background: linear-gradient(135deg, #f0fdf4 0%, #fff 40%); }
.ranking-item.sentiment-negative { background: linear-gradient(135deg, #fff1f2 0%, #fff 40%); }
.ranking-item.sentiment-neutral  { background: #fff; }

/* ── 순위 배지 ────────────────────────────────────────────────────────────── */
.rank-badge {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  font-weight: 700;
  flex-shrink: 0;
  background: #f1f5f9;
  color: #475569;
}
.rank-gold   { background: #fef9c3; color: #b45309; border: 2px solid #f59e0b; }
.rank-silver { background: #f1f5f9; color: #475569; border: 2px solid #94a3b8; }
.rank-bronze { background: #fff7ed; color: #92400e; border: 2px solid #d97706; }

/* ── 썸네일 ───────────────────────────────────────────────────────────────── */
.thumbnail-wrap {
  width: 72px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  background: #f1f5f9;
}
.thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ── 본문 ─────────────────────────────────────────────────────────────────── */
.item-body { flex: 1; min-width: 0; }
.item-meta {
  display: flex;
  gap: 10px;
  font-size: 0.78rem;
  color: #94a3b8;
  margin-bottom: 4px;
}
.source-name { font-weight: 600; color: #64748b; }
.item-title {
  margin: 0 0 8px;
  font-size: 0.97rem;
  font-weight: 600;
  line-height: 1.45;
  color: #1e293b;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* ── 감성 행 ──────────────────────────────────────────────────────────────── */
.sentiment-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* 배지 */
.sentiment-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}
.badge-pos { background: #dcfce7; color: #15803d; }
.badge-neu { background: #f1f5f9; color: #475569; }
.badge-neg { background: #fee2e2; color: #b91c1c; }

/* 확률 바 */
.prob-bars {
  display: flex;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.prob-bar-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 0;
}
.prob-bar {
  height: 6px;
  border-radius: 3px;
  min-width: 4px;
  transition: width 0.3s ease;
}
.prob-bar.pos { background: #4ade80; }
.prob-bar.neu { background: #94a3b8; }
.prob-bar.neg { background: #f87171; }
.prob-label { font-size: 0.7rem; color: #94a3b8; white-space: nowrap; }

/* ── 스코어 ───────────────────────────────────────────────────────────────── */
.score-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  width: 52px;
}
.score-value {
  font-size: 1.5rem;
  font-weight: 800;
  line-height: 1;
}
.score-positive { color: #16a34a; }
.score-negative { color: #dc2626; }
.score-neutral  { color: #64748b; }
.score-unit { font-size: 0.7rem; color: #94a3b8; margin-top: 2px; }

/* ── 반응형 ───────────────────────────────────────────────────────────────── */
@media (max-width: 640px) {
  .thumbnail-wrap { display: none; }
  .prob-bars      { display: none; }
  .sentiment-banner { gap: 0; padding: 12px 12px; }
  .stat-count { font-size: 1.2rem; }
}
</style>
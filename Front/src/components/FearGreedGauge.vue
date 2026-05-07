<!--
  FearGreedGauge.vue
  ==================
  Tier 2.1 (차별화 §2.7) — KOSPI 시장 국면 시각화.

  데이터 소스: GET /api/v1/market/regime
    {date, total_count, tier_a_count, tier_a_ratio, status, weather, message}

  3단계 국면:
    fear (Tier A < 5%)     → 빨간 빛
    neutral (5~10%)        → 노란 빛
    greed (≥ 10%)          → 녹색 빛

  사용:
    <FearGreedGauge />
  메인 페이지 상단·종목 상세 페이지 등에 배치.
-->
<template>
  <div class="fg-gauge" :class="`fg-${status}`" v-if="!loading && data">
    <div class="fg-row" @click="expanded = !expanded" role="button"
         :aria-label="`시장 국면: ${data.message}. 클릭해서 상세 보기.`">
      <div class="fg-ind">
        <span class="fg-icon" aria-hidden="true">{{ icon }}</span>
        <div class="fg-label-box">
          <div class="fg-label">{{ koreanLabel }}</div>
          <div class="fg-sub">Tier A 비율 {{ data.tier_a_ratio }}%</div>
        </div>
      </div>
      <div class="fg-bar">
        <div class="fg-track">
          <div class="fg-fill" :style="{ width: barWidth }"></div>
          <div class="fg-marker" :style="{ left: barWidth }"></div>
        </div>
        <div class="fg-scale">
          <span>Fear</span>
          <span>Neutral</span>
          <span>Greed</span>
        </div>
      </div>
      <button
        type="button"
        class="fg-toggle"
        :aria-expanded="expanded"
        @click.stop="expanded = !expanded"
      >{{ expanded ? '닫기' : '근거' }}</button>
    </div>
    <div class="fg-detail" v-if="expanded">
      <p class="fg-msg">{{ data.message }}</p>
      <dl class="fg-stats">
        <div><dt>기준일</dt><dd>{{ data.date }}</dd></div>
        <div><dt>전체 종목</dt><dd>{{ data.total_count }}</dd></div>
        <div><dt>Tier A 종목</dt><dd>{{ data.tier_a_count }}</dd></div>
        <div><dt>Tier A 비율</dt><dd>{{ data.tier_a_ratio }}%</dd></div>
      </dl>
      <p class="fg-note">
        Tier A 는 일별 백분위 ≥ 93 — Tier A 비율이 높을수록 모델이 매수 신호를
        잘 본 종목이 많다. 5% 미만이면 모델이 보수적, 10% 이상이면 공격적.
      </p>
    </div>
  </div>
  <div class="fg-gauge fg-loading" v-else-if="loading">
    <span class="fg-loading-text">시장 국면 로드 중…</span>
  </div>
  <div class="fg-gauge fg-error" v-else-if="error">
    <span class="fg-error-text">시장 국면 로드 실패</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '@/api/axios'

interface MarketRegime {
  date: string
  model_version: string
  total_count: number
  tier_a_count: number
  tier_a_ratio: number
  status: 'fear' | 'neutral' | 'greed'
  weather: string
  message: string
}

const data = ref<MarketRegime | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const expanded = ref(false)

const status = computed(() => data.value?.status ?? 'neutral')

const icon = computed(() => ({
  fear:    '🌧',
  neutral: '☁',
  greed:   '☀',
}[status.value] ?? '☁'))

const koreanLabel = computed(() => ({
  fear:    '공포 (Fear)',
  neutral: '중립 (Neutral)',
  greed:   '탐욕 (Greed)',
}[status.value] ?? '중립'))

const barWidth = computed(() => {
  // 0~25% 비율 매핑 (실제 데이터에서 30%를 넘지는 않음).
  if (!data.value) return '0%'
  const ratio = Math.min(25, Math.max(0, data.value.tier_a_ratio))
  return `${(ratio / 25) * 100}%`
})

onMounted(async () => {
  try {
    const r = await api.get<MarketRegime>('/market/regime')
    data.value = r.data
  } catch (e: any) {
    console.error('[FearGreedGauge] fetch failed', e)
    error.value = e?.message ?? String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.fg-gauge {
  display: block;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 8px 0;
  background: #f9fafb;
  border-left: 4px solid #6b7280;
  transition: background 0.2s;
}
.fg-fear    { background: #fef2f2; border-left-color: #dc2626; }
.fg-neutral { background: #fffbeb; border-left-color: #f59e0b; }
.fg-greed   { background: #f0fdf4; border-left-color: #16a34a; }

.fg-row {
  display: grid;
  grid-template-columns: minmax(120px, 200px) 1fr auto;
  gap: 14px;
  align-items: center;
  cursor: pointer;
}

.fg-ind { display: flex; align-items: center; gap: 10px; min-width: 0; }
.fg-icon { font-size: 24px; }
.fg-label-box { line-height: 1.2; }
.fg-label { font-size: 14px; font-weight: 700; color: #111827; }
.fg-sub { font-size: 11px; color: #6b7280; margin-top: 2px; }

.fg-bar { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.fg-track {
  position: relative;
  height: 8px;
  border-radius: 9999px;
  background: linear-gradient(to right, #fecaca 0%, #fde68a 40%, #bbf7d0 100%);
  overflow: visible;
}
.fg-fill {
  height: 100%;
  border-radius: 9999px;
  background: rgba(0, 0, 0, 0.05);
}
.fg-marker {
  position: absolute;
  top: -3px;
  width: 4px;
  height: 14px;
  background: #1f2937;
  border-radius: 2px;
  transform: translateX(-50%);
}
.fg-scale {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #9ca3af;
}

.fg-toggle {
  background: transparent;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 11px;
  color: #4b5563;
  cursor: pointer;
}
.fg-toggle:hover { background: #fff; }

.fg-detail {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(0, 0, 0, 0.1);
}
.fg-msg { font-size: 13px; color: #1f2937; margin: 0 0 10px; line-height: 1.5; }
.fg-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px 14px;
  margin: 0 0 8px;
}
.fg-stats div { display: flex; justify-content: space-between; font-size: 12px; }
.fg-stats dt { color: #6b7280; }
.fg-stats dd { color: #111827; font-weight: 600; margin: 0; font-variant-numeric: tabular-nums; }
.fg-note { font-size: 11px; color: #6b7280; margin: 8px 0 0; line-height: 1.5; }

.fg-loading-text, .fg-error-text { font-size: 12px; color: #6b7280; }
.fg-error { background: #fef2f2; border-left-color: #dc2626; }
</style>

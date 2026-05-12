<script setup lang="ts">
// UX W6A — ScreenerTable 다듬기. 토큰 적용, table 구조 유지.
// PrimeVue DataTable 전면 교체는 회귀 위험 큼 → 차차차차기 후보.

import { useRouter } from 'vue-router'
// @ts-ignore
import TierBadge from '@/components/common/TierBadge.vue'

defineProps<{
  items?:   any[]
  total?:   number
  loading?: boolean
  error?:   string | null
}>()
defineEmits<{ (e: 'reset-financial'): void }>()

const router = useRouter()

// tier 색 — W1 도메인 토큰 사용. inline 으로 CSS 변수 호출.
const TIER_VAR: Record<string, string> = {
  A: 'var(--tier-a-bg)',
  B: 'var(--tier-b-bg)',
  C: 'var(--tier-c-bg)',
  D: 'var(--color-neutral-400)',
}

function barColor(score: number): string {
  if (score >= 80) return TIER_VAR.A
  if (score >= 60) return TIER_VAR.B
  if (score >= 40) return TIER_VAR.C
  return TIER_VAR.D
}

function fmt(v: number | null | undefined, suffix = ''): string {
  return v != null ? v.toFixed(1) + suffix : '-'
}

function growthClass(v: number | null | undefined): string {
  if (v == null) return 'screener-table__cell--muted'
  if (v > 0) return 'screener-table__cell--up'
  if (v < 0) return 'screener-table__cell--down'
  return 'screener-table__cell--muted'
}
</script>

<template>
  <div class="screener-table">
    <p class="screener-table__count">
      총 <b>{{ (total ?? 0).toLocaleString() }}</b>개 종목
    </p>

    <div v-if="loading" class="screener-table__loading" aria-busy="true">
      <div class="screener-table__spinner" />
    </div>

    <div v-else-if="error" class="screener-table__empty" role="alert">
      데이터를 불러오지 못했습니다.
    </div>

    <div v-else-if="!items?.length" class="screener-table__empty">
      <p>조건에 맞는 종목이 없습니다.</p>
      <button class="screener-table__reset-btn" @click="$emit('reset-financial')">
        조건 완화하기
      </button>
    </div>

    <div v-else class="screener-table__wrap">
      <table class="screener-table__tbl">
        <thead>
          <tr>
            <th class="screener-table__th screener-table__th--left">순위</th>
            <th class="screener-table__th screener-table__th--left">종목명</th>
            <th class="screener-table__th screener-table__th--left">섹터</th>
            <th class="screener-table__th screener-table__th--left">
              <span class="screener-table__tooltip-host">
                복합점수 <i class="pi pi-info-circle" aria-hidden="true" />
                <span class="screener-table__tooltip">
                  복합점수 = ML점수 × 0.6 + 재무점수 × 0.4<br />
                  재무 데이터 없는 종목은 재무점수 50 적용
                </span>
              </span>
            </th>
            <th class="screener-table__th screener-table__th--right">ML점수</th>
            <th class="screener-table__th screener-table__th--right">재무점수</th>
            <th class="screener-table__th screener-table__th--right">PER</th>
            <th class="screener-table__th screener-table__th--right">PBR</th>
            <th class="screener-table__th screener-table__th--right">ROE</th>
            <th class="screener-table__th screener-table__th--right">부채비율</th>
            <th class="screener-table__th screener-table__th--right">영업이익률</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, idx) in items"
            :key="item.ticker"
            class="screener-table__row"
            @click="router.push('/stocks/' + item.ticker)"
          >
            <td class="screener-table__cell screener-table__cell--muted">{{ idx + 1 }}</td>
            <td class="screener-table__cell">
              <div class="screener-table__name">{{ item.name }}</div>
              <div class="screener-table__ticker">{{ item.ticker }}</div>
            </td>
            <td class="screener-table__cell">
              <span class="screener-table__sector-chip">{{ item.sector }}</span>
            </td>
            <td class="screener-table__cell">
              <div class="screener-table__composite">
                <div class="screener-table__bar">
                  <div
                    class="screener-table__bar-fill"
                    :style="{ width: (item.composite_score ?? 0) + '%', background: barColor(item.composite_score ?? 0) }"
                  />
                </div>
                <span class="screener-table__composite-value">
                  {{ Math.round(item.composite_score ?? 0) }}
                </span>
                <TierBadge :tier="item.tier" />
              </div>
            </td>
            <td class="screener-table__cell screener-table__cell--right">
              {{ Math.round(item.score ?? 0) }}
            </td>
            <td class="screener-table__cell screener-table__cell--right">
              <template v-if="item.finance_score != null">{{ item.finance_score.toFixed(1) }}</template>
              <template v-else><span class="screener-table__cell--muted">- (재무없음)</span></template>
            </td>
            <td class="screener-table__cell screener-table__cell--right screener-table__cell--soft">{{ fmt(item.per) }}</td>
            <td class="screener-table__cell screener-table__cell--right screener-table__cell--soft">{{ fmt(item.pbr) }}</td>
            <td class="screener-table__cell screener-table__cell--right" :class="growthClass(item.roe)">
              {{ fmt(item.roe, '%') }}
            </td>
            <td class="screener-table__cell screener-table__cell--right screener-table__cell--soft">
              {{ fmt(item.debt_ratio, '%') }}
            </td>
            <td class="screener-table__cell screener-table__cell--right" :class="growthClass(item.op_margin)">
              {{ fmt(item.op_margin, '%') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.screener-table {
  display: flex; flex-direction: column; gap: var(--space-3);
  font-family: var(--font-sans);
  color: var(--text-primary);
}
.screener-table__count {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.screener-table__count b { color: var(--text-primary); }

.screener-table__loading {
  display: flex; align-items: center; justify-content: center;
  height: 12rem;
}
.screener-table__spinner {
  width: 24px; height: 24px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary-600);
  border-radius: var(--radius-full);
  animation: spin 1s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }

.screener-table__empty {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-12) var(--space-4);
  color: var(--text-secondary);
  text-align: center;
}
.screener-table__reset-btn {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
}
.screener-table__reset-btn:hover { background: var(--surface-muted); }

.screener-table__wrap {
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
}
.screener-table__tbl {
  width: 100%;
  font-size: var(--text-sm);
  white-space: nowrap;
  border-collapse: collapse;
}
.screener-table__th {
  background: var(--surface-muted);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  padding: var(--space-2) var(--space-3);
  position: sticky; top: 0;
}
.screener-table__th--left  { text-align: left; }
.screener-table__th--right { text-align: right; }

.screener-table__tooltip-host {
  position: relative;
  display: inline-flex; align-items: center; gap: var(--space-1);
  cursor: help;
}
.screener-table__tooltip {
  position: absolute; top: 100%; left: 0;
  margin-top: var(--space-1);
  width: 14rem;
  background: var(--color-neutral-800);
  color: var(--text-inverse);
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  line-height: var(--leading-normal);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  white-space: normal;
  z-index: var(--z-tooltip);
  display: none;
}
.screener-table__tooltip-host:hover .screener-table__tooltip,
.screener-table__tooltip-host:focus-within .screener-table__tooltip {
  display: block;
}

.screener-table__row {
  border-top: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.screener-table__row:hover { background: var(--surface-muted); }

.screener-table__cell {
  padding: var(--space-2) var(--space-3);
}
.screener-table__cell--right { text-align: right; }
.screener-table__cell--muted { color: var(--text-tertiary); font-size: var(--text-xs); }
.screener-table__cell--soft  { color: var(--text-secondary); }
.screener-table__cell--up    { color: var(--color-up); }
.screener-table__cell--down  { color: var(--color-down); }

.screener-table__name   { font-weight: var(--font-medium); color: var(--text-primary); }
.screener-table__ticker { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--text-tertiary); }

.screener-table__sector-chip {
  background: var(--surface-muted);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  border-radius: var(--radius-full);
  padding: 2px var(--space-2);
}

.screener-table__composite {
  display: flex; align-items: center; gap: var(--space-2);
}
.screener-table__bar {
  width: 64px; height: 6px;
  background: var(--border-subtle);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.screener-table__bar-fill {
  height: 100%;
  border-radius: var(--radius-sm);
}
.screener-table__composite-value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}
</style>

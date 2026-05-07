<!--
  TopFactorsList.vue
  ==================
  Tier 1.3 (PRD §4.4 / 차별화 §2.3) — SHAP 기여 피처를 자연어로 표시.

  사용:
    <TopFactorsList :factors="stock.top_factors" />

  추천 카드 펼침 영역, 종목 상세 페이지 "추천 이유" 섹션에서 사용.
  factors 가 비어있거나 undefined 면 "이유 데이터 미적재" 안내를 보여준다 — 침묵 실패 금지.
-->
<template>
  <div class="top-factors">
    <p v-if="!factors || factors.length === 0" class="empty">
      이 종목의 추천 이유 데이터가 아직 적재되지 않았습니다.
    </p>
    <ul v-else class="factor-list">
      <li
        v-for="f in factors"
        :key="f.feature"
        class="factor-item"
        :class="`factor-${f.direction}`"
      >
        <span class="factor-icon" aria-hidden="true">
          {{ f.direction === 'positive' ? '▲' : '▼' }}
        </span>
        <span class="factor-label">{{ f.label }}</span>
        <span
          class="factor-contrib"
          :title="`SHAP 기여도: ${formatContribution(f.contribution)}`"
        >
          {{ formatContribution(f.contribution) }}
        </span>
      </li>
    </ul>
    <p v-if="factors && factors.length > 0" class="caption">
      v9 LightGBM SHAP 분석 — 절대값 기준 상위 {{ factors.length }}개
    </p>
  </div>
</template>

<script setup lang="ts">
import type { TopFactor } from '@/api'

defineProps<{
  factors?: TopFactor[] | null
}>()

function formatContribution(c: number): string {
  const sign = c >= 0 ? '+' : ''
  return `${sign}${c.toFixed(3)}`
}
</script>

<style scoped>
.top-factors {
  font-size: 13px;
  line-height: 1.5;
}

.empty {
  color: #6b7280;
  font-style: italic;
  margin: 4px 0;
}

.factor-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.factor-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  border-left: 3px solid;
}

.factor-positive {
  background: #f0fdf4;
  border-left-color: #16a34a;
}

.factor-negative {
  background: #fef2f2;
  border-left-color: #dc2626;
}

.factor-icon {
  font-size: 11px;
}

.factor-positive .factor-icon { color: #16a34a; }
.factor-negative .factor-icon { color: #dc2626; }

.factor-label {
  color: #1f2937;
}

.factor-contrib {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #4b5563;
  font-weight: 500;
}

.caption {
  margin: 8px 0 0;
  font-size: 11px;
  color: #9ca3af;
  font-style: italic;
}
</style>

<script setup lang="ts">
// UX W2 — KOSPI 폭락장 배너 (백엔드 W8 market_regime).
// 결정: 노랑 배경 + 빨강 border 절충 (사용자 명시).
// regime !== 'extreme_volatility' 면 렌더링 안 함.

interface Props {
  regime: 'normal' | 'extreme_volatility' | string | null | undefined
}

const props = defineProps<Props>()
const show = () => props.regime === 'extreme_volatility'
</script>

<template>
  <div v-if="show()" role="alert" class="regime-banner">
    <i class="pi pi-exclamation-triangle regime-banner__icon" aria-hidden="true" />
    <div class="regime-banner__body">
      <strong>시장 변동성 경고</strong>
      <span>KOSPI 지수 일중 변화가 크게 발생했습니다. 신중한 의사결정을 권장합니다.</span>
      <small>본 정보는 자문이 아닙니다.</small>
    </div>
  </div>
</template>

<style scoped>
.regime-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  /* 노랑 배경 + 빨강 border — 사용자 결정 (절충) */
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border-left: 4px solid var(--color-danger);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
}
.regime-banner__icon { font-size: var(--text-xl); margin-top: 2px; }
.regime-banner__body { display: flex; flex-direction: column; gap: var(--space-1); }
.regime-banner__body strong { font-weight: var(--font-semibold); }
.regime-banner__body small  { font-size: var(--text-xs); opacity: 0.75; }
</style>

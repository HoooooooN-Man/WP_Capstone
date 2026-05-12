<script setup lang="ts">
// UX W2 — 신규 상장 60일 미만 종목 배지 (백엔드 W8 coverage_status).
// status === 'ok' 면 렌더링 안 함 (null).

interface Props {
  status: 'ok' | 'insufficient_data' | string | null | undefined
  availableDays?: number
  threshold?: number
}

const props = withDefaults(defineProps<Props>(), { threshold: 60 })
const show = () => props.status === 'insufficient_data'
</script>

<template>
  <div v-if="show()" role="status" class="coverage-badge">
    <i class="pi pi-info-circle coverage-badge__icon" aria-hidden="true" />
    <span class="coverage-badge__text">
      <strong>신규 상장 — 분석 충분치 않음</strong>
      <small v-if="availableDays != null">
        ({{ availableDays }}일 / {{ threshold }}일 기준)
      </small>
    </span>
  </div>
</template>

<style scoped>
.coverage-badge {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--coverage-insufficient-bg);
  color: var(--coverage-insufficient-text);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-warning);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}
.coverage-badge__icon { font-size: var(--text-lg); margin-top: 2px; }
.coverage-badge__text { display: flex; flex-direction: column; gap: var(--space-1); }
.coverage-badge__text small {
  font-size: var(--text-xs);
  opacity: 0.85;
}
</style>

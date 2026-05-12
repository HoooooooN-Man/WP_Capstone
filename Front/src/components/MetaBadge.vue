<script setup lang="ts">
// UX W2 — 응답 meta 의 작은 정보 노출 (model_version·cohort·diversify).
// 결정: 정적 (클릭 모달 기각 — W3 통합 시 재검토).

interface Props {
  label: string                          // "모델", "코호트", "다양성"
  value: string | null | undefined       // 표시 값. null 시 컴포넌트 숨김.
  variant?: 'default' | 'subtle' | 'info'
  tooltip?: string
}

const props = withDefaults(defineProps<Props>(), { variant: 'default' })
</script>

<template>
  <span v-if="value" class="meta-badge" :data-variant="variant" :title="tooltip">
    <span class="meta-badge__label">{{ label }}</span>
    <span class="meta-badge__sep">:</span>
    <span class="meta-badge__value">{{ value }}</span>
  </span>
</template>

<style scoped>
.meta-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-family: var(--font-sans);
  line-height: var(--leading-tight);
  background: var(--surface-muted);
  color: var(--text-secondary);
  white-space: nowrap;
}
.meta-badge[data-variant='info'] {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}
.meta-badge[data-variant='subtle'] {
  background: transparent;
  color: var(--text-tertiary);
}
.meta-badge__label { font-weight: var(--font-medium); }
.meta-badge__sep   { opacity: 0.5; }
.meta-badge__value { font-weight: var(--font-semibold); }
</style>

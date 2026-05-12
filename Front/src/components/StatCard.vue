<script setup lang="ts">
// UX W5 — MyPage 활동 통계 카드. 큰 숫자 + 작은 label.

interface Props {
  label: string
  value: string | number | null | undefined
  suffix?: string
}

const props = defineProps<Props>()
</script>

<template>
  <div class="stat-card">
    <span class="stat-card__value">
      <template v-if="value != null && value !== ''">{{ value }}{{ suffix ?? '' }}</template>
      <template v-else>-</template>
    </span>
    <span class="stat-card__label">{{ label }}</span>
  </div>
</template>

<style scoped>
.stat-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-1);
  padding: var(--space-4);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  text-align: center;
  min-width: 96px;
}
.stat-card__value {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1;
}
.stat-card__label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
</style>

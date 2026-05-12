<script setup lang="ts">
// UX W5 — cohort radio 그룹 (Onboarding 5번째 step + 변경 모달 공용).
// 큰 카드 라디오. 한 줄에 1개 (모바일 우선).

import { COHORT_META, type CohortKey } from '@/composables/useCohortMeta'

interface Props {
  modelValue: CohortKey | null
  name?: string                    // radio group 이름 (form 안에서 충돌 방지)
}

const props = withDefaults(defineProps<Props>(), { name: 'cohort' })
const emit  = defineEmits<{ (e: 'update:modelValue', v: CohortKey): void }>()

function onChange(key: CohortKey) {
  emit('update:modelValue', key)
}
</script>

<template>
  <fieldset class="cohort-picker">
    <legend class="cohort-picker__legend">관심사 선택</legend>
    <label
      v-for="m in COHORT_META"
      :key="m.key"
      :class="['cohort-picker__option', { 'is-selected': modelValue === m.key }]"
    >
      <input
        type="radio"
        :name="name"
        :value="m.key"
        :checked="modelValue === m.key"
        class="cohort-picker__radio"
        @change="onChange(m.key)"
      />
      <i :class="['pi', m.icon, 'cohort-picker__icon']" aria-hidden="true" />
      <div class="cohort-picker__body">
        <strong>{{ m.label }}</strong>
        <span>{{ m.description }}</span>
      </div>
    </label>
  </fieldset>
</template>

<style scoped>
.cohort-picker {
  border: 0; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: var(--space-2);
  font-family: var(--font-sans);
}
.cohort-picker__legend {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}
.cohort-picker__option {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out),
              background var(--duration-fast) var(--ease-out);
}
.cohort-picker__option:hover { background: var(--surface-muted); }
.cohort-picker__option.is-selected {
  border-color: var(--color-primary-600);
  background: var(--color-primary-50);
}
.cohort-picker__option:focus-within {
  outline: none; box-shadow: var(--shadow-focus);
}
.cohort-picker__radio {
  /* 시각 hide, 접근성·키보드 유지 */
  position: absolute; opacity: 0; pointer-events: none;
}
.cohort-picker__icon {
  font-size: var(--text-xl);
  color: var(--color-primary-600);
  width: 2rem; text-align: center;
}
.cohort-picker__body { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.cohort-picker__body strong {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}
.cohort-picker__body span {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
</style>

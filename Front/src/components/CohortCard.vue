<script setup lang="ts">
// UX W5 — MyPage "내 관심사" 큰 카드. cohort 1개 표시.
// 결정: 권고 수용 — 모달 변경 액션 caller 가 emit 처리.

import { computed } from 'vue'
import { getCohortMeta, type CohortKey } from '@/composables/useCohortMeta'

interface Props {
  cohort: CohortKey | string | null | undefined
  showChangeButton?: boolean
}

const props = withDefaults(defineProps<Props>(), { showChangeButton: true })
const emit  = defineEmits<{ (e: 'change'): void }>()

const meta = computed(() => getCohortMeta(props.cohort))
</script>

<template>
  <div class="cohort-card">
    <div v-if="meta" class="cohort-card__inner">
      <i :class="['pi', meta.icon, 'cohort-card__icon']" aria-hidden="true" />
      <div class="cohort-card__body">
        <strong class="cohort-card__label">{{ meta.label }}</strong>
        <p class="cohort-card__description">{{ meta.description }}</p>
      </div>
      <button
        v-if="showChangeButton"
        class="cohort-card__change"
        @click="emit('change')"
      >
        변경
      </button>
    </div>
    <div v-else class="cohort-card__empty">
      <p>관심사가 설정되지 않았습니다.</p>
      <button class="cohort-card__change" @click="emit('change')">설정하기</button>
    </div>
  </div>
</template>

<style scoped>
.cohort-card {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
  font-family: var(--font-sans);
}
.cohort-card__inner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.cohort-card__icon {
  font-size: 2rem;
  color: var(--color-primary-600);
  width: 3rem; height: 3rem;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-primary-50);
  border-radius: var(--radius-full);
}
.cohort-card__body { flex: 1; display: flex; flex-direction: column; gap: var(--space-1); }
.cohort-card__label {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}
.cohort-card__description {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.cohort-card__change {
  padding: var(--space-2) var(--space-4);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: inherit;
  color: var(--text-secondary);
  cursor: pointer;
}
.cohort-card__change:hover { background: var(--surface-muted); }
.cohort-card__change:focus-visible { outline: none; box-shadow: var(--shadow-focus); }
.cohort-card__empty {
  display: flex; justify-content: space-between; align-items: center;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}
</style>

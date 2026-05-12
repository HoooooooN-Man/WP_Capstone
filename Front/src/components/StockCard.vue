<script setup lang="ts">
// UX W2 — 일반 종목 카드 (검색·랭킹·관심).
// 결정: compact 자동 (media query 768px 기준).

type Tier = 'A' | 'B' | 'C' | 'D'

interface Props {
  ticker: string
  name: string
  sector?: string
  price?: number
  changePercent?: number
  score?: number
  tier?: Tier | null
}

const props = defineProps<Props>()
const emit  = defineEmits<{ (e: 'click'): void }>()

function formatPrice(v: number): string {
  return v.toLocaleString('ko-KR')
}

function formatChange(v: number): string {
  const sign = v > 0 ? '▲' : v < 0 ? '▼' : '-'
  return `${sign} ${Math.abs(v).toFixed(2)}%`
}

function changeClass(v: number | undefined): string {
  if (v == null) return ''
  if (v > 0) return 'stock-card__change--up'
  if (v < 0) return 'stock-card__change--down'
  return ''
}
</script>

<template>
  <li
    class="stock-card"
    role="button"
    tabindex="0"
    @click="emit('click')"
    @keydown.enter="emit('click')"
  >
    <div class="stock-card__left">
      <span v-if="tier" class="stock-card__tier" :data-tier="tier">{{ tier }}</span>
      <div class="stock-card__identity">
        <span class="stock-card__ticker">{{ ticker }}</span>
        <span class="stock-card__name">{{ name }}</span>
        <span v-if="sector" class="stock-card__sector">· {{ sector }}</span>
      </div>
    </div>
    <div class="stock-card__right">
      <span v-if="price != null" class="stock-card__price">{{ formatPrice(price) }}</span>
      <span
        v-if="changePercent != null"
        :class="['stock-card__change', changeClass(changePercent)]"
      >
        {{ formatChange(changePercent) }}
      </span>
      <span v-if="score != null" class="stock-card__score">{{ score }}점</span>
    </div>
  </li>
</template>

<style scoped>
.stock-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  list-style: none;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.stock-card:hover         { background: var(--surface-muted); }
.stock-card:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

.stock-card__left {
  display: flex; align-items: center; gap: var(--space-2);
  min-width: 0; flex: 1;
}
.stock-card__tier {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.5rem; height: 1.5rem;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
}
.stock-card__tier[data-tier='A'] { background: var(--tier-a-bg); color: var(--tier-a-text); }
.stock-card__tier[data-tier='B'] { background: var(--tier-b-bg); color: var(--tier-b-text); }
.stock-card__tier[data-tier='C'] { background: var(--tier-c-bg); color: var(--tier-c-text); }
.stock-card__tier[data-tier='D'] { background: var(--color-neutral-200); color: var(--color-neutral-600); }

.stock-card__identity {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--space-2);
  min-width: 0;
}
.stock-card__ticker { color: var(--text-secondary); font-size: var(--text-sm); }
.stock-card__name   { color: var(--text-primary);   font-weight: var(--font-medium); }
.stock-card__sector { color: var(--text-tertiary);  font-size: var(--text-sm); }

.stock-card__right {
  display: flex; flex-direction: column; align-items: flex-end; gap: var(--space-1);
  text-align: right;
}
.stock-card__price  { font-weight: var(--font-semibold); }
.stock-card__change { font-size: var(--text-sm); font-weight: var(--font-medium); }
.stock-card__change--up   { color: var(--color-up); }
.stock-card__change--down { color: var(--color-down); }
.stock-card__score {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* compact 자동 — 768px 미만에서 1행 밀착 */
@media (max-width: 768px) {
  .stock-card {
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-sm);
  }
  .stock-card__right { flex-direction: row; gap: var(--space-2); align-items: baseline; }
  .stock-card__score { display: none; }
}
</style>

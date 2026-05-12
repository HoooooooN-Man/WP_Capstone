<script setup lang="ts">
// UX W5 — Watchlist row. StockCard 와 결 같으나 제거 액션 포함.
// 결정: 권고 수용 — StockCard slot 대신 별 컴포넌트 (도메인 분리).
//        제거 = 낙관 + Undo toast (caller 가 toast 책임).

interface Props {
  ticker: string
  name: string
  sector?: string
  price?: number
  changePercent?: number
}

const props = defineProps<Props>()
const emit  = defineEmits<{
  (e: 'click'): void
  (e: 'remove'): void
}>()

function fmtPrice(v: number | undefined): string {
  if (v == null || !isFinite(v)) return '-'
  return v.toLocaleString('ko-KR')
}

function fmtChange(v: number | undefined): string {
  if (v == null || !isFinite(v)) return '-'
  const sign = v > 0 ? '▲' : v < 0 ? '▼' : '-'
  return `${sign} ${Math.abs(v).toFixed(2)}%`
}

function changeClass(v: number | undefined): string {
  if (v == null || v === 0) return ''
  return v > 0 ? 'watchlist-item__change--up' : 'watchlist-item__change--down'
}

function onRemove(ev: Event) {
  ev.stopPropagation()
  emit('remove')
}
</script>

<template>
  <li
    class="watchlist-item"
    role="button"
    tabindex="0"
    @click="emit('click')"
    @keydown.enter="emit('click')"
  >
    <div class="watchlist-item__left">
      <span class="watchlist-item__ticker">{{ ticker }}</span>
      <span class="watchlist-item__name">{{ name }}</span>
      <span v-if="sector" class="watchlist-item__sector">· {{ sector }}</span>
    </div>
    <div class="watchlist-item__right">
      <span v-if="price != null" class="watchlist-item__price">{{ fmtPrice(price) }}</span>
      <span
        v-if="changePercent != null"
        :class="['watchlist-item__change', changeClass(changePercent)]"
      >
        {{ fmtChange(changePercent) }}
      </span>
      <button
        class="watchlist-item__remove"
        :aria-label="`관심종목에서 ${name} 제거`"
        @click="onRemove"
        @keydown.enter.stop
      >
        <i class="pi pi-times" aria-hidden="true" />
      </button>
    </div>
  </li>
</template>

<style scoped>
.watchlist-item {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-card);
  border-bottom: 1px solid var(--border-subtle);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  list-style: none;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.watchlist-item:hover { background: var(--surface-muted); }
.watchlist-item:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

.watchlist-item__left {
  display: flex; align-items: baseline; gap: var(--space-2); min-width: 0;
}
.watchlist-item__ticker { color: var(--text-secondary); font-size: var(--text-sm); }
.watchlist-item__name   { color: var(--text-primary);   font-weight: var(--font-medium); }
.watchlist-item__sector { color: var(--text-tertiary);  font-size: var(--text-sm); }

.watchlist-item__right {
  display: flex; align-items: center; gap: var(--space-3);
}
.watchlist-item__price  { font-weight: var(--font-semibold); }
.watchlist-item__change { font-size: var(--text-sm); font-weight: var(--font-medium); }
.watchlist-item__change--up   { color: var(--color-up); }
.watchlist-item__change--down { color: var(--color-down); }
.watchlist-item__remove {
  background: transparent; border: 0; cursor: pointer;
  color: var(--text-tertiary);
  padding: var(--space-1);
  font-size: var(--text-base);
}
.watchlist-item__remove:hover { color: var(--color-danger); }
.watchlist-item__remove:focus-visible { outline: none; box-shadow: var(--shadow-focus); }
</style>

<script setup lang="ts">
// UX W5 C2 — WatchlistView 신규.
// 결정: 정렬 default 추가 순, 제거 = 낙관 + PrimeVue Toast Undo (5초, 하단 중앙).

import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import WatchlistItem from '@/components/WatchlistItem.vue'
import { useWatchlist, sortTickers, type SortKey } from '@/composables/useWatchlist'

// @ts-ignore
import { useWatchlistStore } from '@/stores/watchlist'

const router = useRouter()
const watch_ = useWatchlistStore()
const toast  = useToast()

const sortBy = ref<SortKey>('recent')

const { visibleTickers, removeWithUndo, undoRemove } = useWatchlist({
  tickers: watch_.tickers ? watch_.tickers : { value: [] },
  remove:  (t: string) => watch_.remove?.(t) ?? watch_.toggle?.(t),
  restore: (t: string) => watch_.add?.(t) ?? watch_.toggle?.(t),
  toggle:  (t: string) => watch_.toggle?.(t),
})

const items = computed(() =>
  visibleTickers.value.map(t => ({ ticker: t, name: t })),
)
const sorted = computed(() => sortTickers(items.value, sortBy.value))

const sortOptions: { value: SortKey; label: string }[] = [
  { value: 'recent', label: '추가 순' },
  { value: 'name',   label: '종목명 순' },
]

function goDetail(ticker: string) {
  router.push(`/stock/${ticker}`)
}

function onRemove(ticker: string) {
  removeWithUndo(ticker, 5000)
  toast.add({
    severity: 'info',
    summary:  '관심종목에서 제거됨',
    detail:   ticker,
    life:     5000,
    closable: true,
    group:    'undo',
  })
}

function onUndo(ticker: string) {
  if (undoRemove(ticker)) {
    toast.removeAllGroups()
    toast.add({
      severity: 'success',
      summary:  '되돌렸습니다',
      detail:   ticker,
      life:     2000,
    })
  }
}

function goRecommend() { router.push('/recommend') }
</script>

<template>
  <div class="watchlist-view">
    <header class="watchlist-view__header">
      <h1>관심종목</h1>
    </header>

    <div v-if="items.length" class="watchlist-view__toolbar">
      <label class="watchlist-view__sort-label">
        정렬
        <select v-model="sortBy" class="watchlist-view__sort-select">
          <option v-for="opt in sortOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </label>
      <span class="watchlist-view__count">{{ items.length }}개</span>
    </div>

    <ul v-if="sorted.length" class="watchlist-view__list">
      <WatchlistItem
        v-for="item in sorted"
        :key="item.ticker"
        :ticker="item.ticker"
        :name="item.name"
        @click="goDetail(item.ticker)"
        @remove="onRemove(item.ticker)"
      />
    </ul>

    <div v-else class="watchlist-view__empty">
      <i class="pi pi-bookmark" aria-hidden="true" />
      <p>관심종목이 없습니다.</p>
      <button class="watchlist-view__cta" @click="goRecommend">
        추천에서 추가하기 →
      </button>
    </div>

    <!-- Undo toast (그룹 'undo' — 위 onRemove 와 onUndo 가 사용) -->
    <Toast position="bottom-center" group="undo">
      <template #message="slotProps">
        <div class="undo-toast">
          <i class="pi pi-info-circle" aria-hidden="true" />
          <div class="undo-toast__body">
            <strong>{{ slotProps.message.summary }}</strong>
            <span>{{ slotProps.message.detail }}</span>
          </div>
          <button
            class="undo-toast__btn"
            @click="onUndo(String(slotProps.message.detail ?? ''))"
          >
            되돌리기
          </button>
        </div>
      </template>
    </Toast>
    <Toast position="bottom-center" />
  </div>
</template>

<style scoped>
.watchlist-view {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--layout-content-pad);
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.watchlist-view__header {
  padding: var(--space-6) 0 var(--space-4);
}
.watchlist-view__header h1 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.watchlist-view__toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-2) 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.watchlist-view__sort-label {
  display: inline-flex; align-items: center; gap: var(--space-2);
}
.watchlist-view__sort-select {
  padding: var(--space-1) var(--space-2);
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-family: inherit; font-size: inherit;
  color: var(--text-primary);
}
.watchlist-view__count { font-weight: var(--font-medium); }

.watchlist-view__list {
  list-style: none; padding: 0; margin: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.watchlist-view__empty {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-2);
  padding: var(--space-12);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  color: var(--text-secondary); text-align: center;
}
.watchlist-view__empty i { font-size: 2rem; color: var(--text-tertiary); }
.watchlist-view__cta {
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border: 0;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
  margin-top: var(--space-2);
}

/* Undo toast 커스텀 — 하단 중앙 (PrimeVue position) */
.undo-toast {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-card);
  color: var(--text-primary);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-subtle);
  font-family: var(--font-sans);
}
.undo-toast i { color: var(--color-info, var(--color-primary-600)); }
.undo-toast__body { display: flex; flex-direction: column; }
.undo-toast__body strong { font-size: var(--text-sm); font-weight: var(--font-semibold); }
.undo-toast__body span   { font-size: var(--text-xs); color: var(--text-secondary); }
.undo-toast__btn {
  background: transparent;
  border: 0; padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-primary-600);
  cursor: pointer;
  font-family: inherit;
}
.undo-toast__btn:hover { text-decoration: underline; }
</style>

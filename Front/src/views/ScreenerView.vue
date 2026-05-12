<script setup lang="ts">
// UX W6A — ScreenerView 다듬기. design-tokens 적용, 구조·로직 유지.
// store·router·필터 동기 그대로.
// @ts-nocheck — 캡스톤 시기 store 가 .js (점진적 마이그레이션).

import { ref, watchEffect, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
// @ts-ignore
import { useScreenerStore } from '@/stores/screener'
import FilterSidebar from '@/components/screener/FilterSidebar.vue'
import ScreenerTable from '@/components/screener/ScreenerTable.vue'

const route  = useRoute()
const router = useRouter()
const store  = useScreenerStore()
const filterSheetOpen = ref(false)

const fetchDebounced = useDebounceFn(() => store.fetchScreener(), 500)

function onFilterChange({ key, value }: { key: string; value: any }) {
  if (key === '_reload') { store.fetchScreener(); return }
  store.setFilter(key, value)
  fetchDebounced()
}

function onResetFinancial() { store.resetFinancialFilters(); store.fetchScreener() }
function onResetAll()       { store.resetAllFilters();       store.fetchScreener() }

watchEffect(() => {
  const q: Record<string, string | number> = {}
  const f = store.filters
  if (f.sort_by)   q.sort = f.sort_by
  if (f.min_roe)   q.min_roe = f.min_roe
  if (f.max_per)   q.max_per = f.max_per
  if (f.min_score) q.min_score = f.min_score
  if (f.sector)    q.sector = f.sector
  router.replace({ query: q })
})

onMounted(() => {
  const q = route.query
  if (q.sort)      store.setFilter('sort_by',   q.sort)
  if (q.min_roe)   store.setFilter('min_roe',   Number(q.min_roe))
  if (q.max_per)   store.setFilter('max_per',   Number(q.max_per))
  if (q.min_score) store.setFilter('min_score', Number(q.min_score))
  if (q.sector)    store.setFilter('sector',    q.sector)
  store.fetchScreener()
})
</script>

<template>
  <div class="screener-view">
    <header class="screener-view__header">
      <div>
        <h1>스크리너</h1>
        <p>ML 점수와 재무 지표를 조합해 종목을 필터링합니다.</p>
      </div>
      <button
        class="screener-view__filter-btn"
        @click="filterSheetOpen = true"
        aria-label="필터 열기"
      >
        <i class="pi pi-sliders-h" aria-hidden="true" /> 필터
      </button>
    </header>

    <div class="screener-view__layout">
      <FilterSidebar
        class="screener-view__sidebar"
        :filters="store.filters"
        @filter-change="onFilterChange"
        @reset-financial="onResetFinancial"
        @reset-all="onResetAll"
      />
      <ScreenerTable
        :items="store.items"
        :total="store.total"
        :loading="store.loading"
        :error="store.error"
        @reset-financial="onResetFinancial"
      />
    </div>

    <!-- 모바일 Bottom Sheet -->
    <Teleport to="body">
      <Transition name="sheet">
        <div v-if="filterSheetOpen" class="filter-sheet" role="dialog" aria-modal="true">
          <div class="filter-sheet__backdrop" @click="filterSheetOpen = false" />
          <div class="filter-sheet__panel">
            <div class="filter-sheet__handle" />
            <div class="filter-sheet__head">
              <h3>필터</h3>
              <button
                class="filter-sheet__close"
                aria-label="닫기"
                @click="filterSheetOpen = false"
              ><i class="pi pi-times" /></button>
            </div>
            <div class="filter-sheet__body">
              <FilterSidebar
                :filters="store.filters"
                @filter-change="onFilterChange"
                @reset-financial="onResetFinancial"
                @reset-all="onResetAll"
              />
            </div>
            <div class="filter-sheet__footer">
              <button class="filter-sheet__apply" @click="filterSheetOpen = false">
                적용하기
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.screener-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-4) var(--layout-content-pad) var(--space-12);
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.screener-view__header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: var(--space-4);
}
.screener-view__header h1 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}
.screener-view__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.screener-view__filter-btn {
  display: none;
  align-items: center; gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;
}
.screener-view__filter-btn:hover { background: var(--surface-muted); }

.screener-view__layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: var(--space-6);
  align-items: start;
}

/* Bottom sheet */
.filter-sheet {
  position: fixed; inset: 0;
  z-index: var(--z-modal);
}
.filter-sheet__backdrop {
  position: absolute; inset: 0;
  background: var(--surface-overlay);
}
.filter-sheet__panel {
  position: absolute; left: 0; right: 0; bottom: 0;
  background: var(--surface-card);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  max-height: 85vh;
  display: flex; flex-direction: column;
}
.filter-sheet__handle {
  width: 40px; height: 4px;
  background: var(--border-default);
  border-radius: var(--radius-full);
  margin: var(--space-3) auto var(--space-2);
}
.filter-sheet__head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 var(--space-5) var(--space-3);
}
.filter-sheet__head h3 { margin: 0; font-size: var(--text-lg); font-weight: var(--font-semibold); }
.filter-sheet__close {
  background: transparent; border: 0; cursor: pointer;
  color: var(--text-tertiary); font-size: var(--text-lg);
}
.filter-sheet__body {
  flex: 1; overflow-y: auto;
  padding: 0 var(--space-2) var(--space-4);
}
.filter-sheet__footer { padding: var(--space-3) var(--space-4) var(--space-6); }
.filter-sheet__apply {
  width: 100%; padding: var(--space-3);
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border: 0; border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  font-family: inherit;
  cursor: pointer;
}

.sheet-enter-active, .sheet-leave-active { transition: opacity var(--duration-normal); }
.sheet-enter-from, .sheet-leave-to       { opacity: 0; }

@media (max-width: 768px) {
  .screener-view__filter-btn { display: inline-flex; }
  .screener-view__layout     { grid-template-columns: 1fr; }
  .screener-view__sidebar    { display: none; }
}
</style>

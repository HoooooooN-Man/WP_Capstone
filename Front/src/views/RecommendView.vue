<script setup lang="ts">
// UX W3 — 추천 메인 화면 재설계.
// 결정 박제 (w3-recommend-view-draft.md):
//   §1·2: 헤드라인 + subtitle 단순 텍스트, as_of_date "M월 D일 기준"
//   §3   : top_k=20, 빈 상태 CTA·"신규 상장 포함" 기각
//   §4   : diversify default=none, 고급 옵션 default 접힘, embedding 경고 "실험적"
//   §5   : 비로그인 CTA = (b) 5번째 카드 자리 + (c) 그리드 끝 큰 CTA
//   §6   : store 안 만듦, Vue Query 단독, URL query 동기, staleTime 5분
//   §7·8 : ARIA 기본만, composable 분리

import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import RecommendCard from '@/components/RecommendCard.vue'
import MarketRegimeBanner from '@/components/MarketRegimeBanner.vue'
import {
  useRecommendations, formatAsOfDate, COHORT_LABEL, DIVERSIFY_LABEL,
  type DiversifyMode,
} from '@/composables/useRecommendations'

// @ts-ignore — 기존 stores (Pinia)
import { useAuthStore } from '@/stores/auth.js'
// @ts-ignore
import { useWatchlistStore } from '@/stores/watchlist.js'

const router = useRouter()
const route  = useRoute()
const auth   = useAuthStore()
const watch_ = useWatchlistStore()

// ── URL query 동기 ──────────────────────────────────────────────────────────
const topK = computed<number>({
  get: () => Number(route.query.top_k ?? 20) || 20,
  set: v => router.replace({ query: { ...route.query, top_k: String(v) } }),
})
const diversify = computed<DiversifyMode>({
  get: () => (route.query.diversify as DiversifyMode) ?? 'none',
  set: v  => router.replace({
    query: { ...route.query, diversify: v === 'none' ? undefined : v },
  }),
})

// 고급 옵션 펼침 (UI state, URL 동기 안 함)
const advancedOpen = ref(false)

// ── 데이터 ────────────────────────────────────────────────────────────────
const { items, meta, isLoading, isError, refetch } = useRecommendations({
  topK, diversify,
})

const subtitleParts = computed<string[]>(() => {
  const parts: string[] = []
  if (meta.value.model_version) parts.push(meta.value.model_version)
  if (meta.value.cohort)        parts.push(COHORT_LABEL[meta.value.cohort] ?? meta.value.cohort)
  parts.push(`${items.value.length}개`)
  if (meta.value.as_of_date)    parts.push(formatAsOfDate(meta.value.as_of_date))
  return parts
})

const headline = computed(() =>
  auth.user?.name ? `${auth.user.name}님의 추천` : '오늘의 추천'
)

const watchedSet = computed(() => new Set<string>(watch_.tickers ?? []))

// 비로그인 CTA — (b) 5번째 카드 자리 + (c) 그리드 끝 큰 CTA
const showInlineCTA = computed(() => !auth.isAuthenticated && items.value.length >= 4)
const showFooterCTA = computed(() => !auth.isAuthenticated)

function onCardClick(ticker: string) {
  router.push(`/stock/${ticker}`)
}

function onWatchToggle(ticker: string) {
  if (!auth.isAuthenticated) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  watch_.toggle?.(ticker)
}

function goLogin() {
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

function resetFilters() {
  router.replace({ query: { top_k: '20' } })
}
</script>

<template>
  <div class="recommend-view">
    <!-- 시장 폭락 배너 (regime !== normal 시만 표시) -->
    <MarketRegimeBanner :regime="meta.market_regime" />

    <header class="recommend-view__header">
      <h1 class="recommend-view__title">{{ headline }}</h1>
      <p class="recommend-view__subtitle">
        <template v-for="(part, i) in subtitleParts" :key="i">
          <span>{{ part }}</span>
          <span v-if="i < subtitleParts.length - 1" class="recommend-view__dot">·</span>
        </template>
      </p>
      <div class="recommend-view__actions">
        <button
          class="recommend-view__toggle"
          :aria-expanded="advancedOpen"
          @click="advancedOpen = !advancedOpen"
        >
          <i class="pi pi-cog" /> 고급 옵션
        </button>
      </div>
    </header>

    <!-- 고급 옵션 (diversify radio + embedding 경고) -->
    <aside v-if="advancedOpen" class="recommend-view__advanced" aria-label="고급 옵션">
      <fieldset class="advanced-group">
        <legend>다양성</legend>
        <label
          v-for="opt in (['none','correlation','sector','embedding'] as DiversifyMode[])"
          :key="opt"
          class="advanced-radio"
        >
          <input
            type="radio"
            name="diversify"
            :value="opt"
            :checked="diversify === opt"
            @change="diversify = opt"
          />
          <span class="advanced-radio__label">{{ DIVERSIFY_LABEL[opt] }}</span>
          <small v-if="opt === 'embedding'" class="advanced-radio__warn">
            실험적 — W5 ablation 신호 약함
          </small>
        </label>
      </fieldset>
    </aside>

    <!-- 로딩 skeleton -->
    <div v-if="isLoading" class="recommend-view__grid" aria-busy="true">
      <div v-for="i in 9" :key="i" class="skeleton-card">
        <div class="skeleton-line skeleton-line--sm" />
        <div class="skeleton-line skeleton-line--lg" />
        <div class="skeleton-line skeleton-line--md" />
      </div>
    </div>

    <!-- 에러 -->
    <div v-else-if="isError" class="recommend-view__error" role="alert">
      <i class="pi pi-exclamation-triangle" />
      <p>추천 데이터를 불러오지 못했습니다.</p>
      <button class="recommend-view__retry" @click="refetch()">다시 시도</button>
    </div>

    <!-- 빈 상태 -->
    <div v-else-if="items.length === 0" class="recommend-view__empty">
      <i class="pi pi-inbox" />
      <p>오늘은 추천 종목이 없습니다.</p>
      <small>데이터가 갱신되면 다시 시도해주세요.</small>
      <button class="recommend-view__retry" @click="resetFilters">고급 옵션 재설정</button>
    </div>

    <!-- 추천 grid -->
    <main v-else class="recommend-view__grid">
      <template v-for="(rec, idx) in items" :key="rec.ticker">
        <RecommendCard
          :ticker="rec.ticker"
          :name="rec.name"
          :sector="rec.sector ?? undefined"
          :score="rec.score"
          :tier="rec.tier"
          :rank="rec.rank_in_date"
          :cohort-match="meta.cohort ?? null"
          :diversify="meta.diversify ?? null"
          :is-watched="watchedSet.has(rec.ticker)"
          @click="onCardClick(rec.ticker)"
          @watch-toggle="onWatchToggle(rec.ticker)"
        />
        <!-- (b) 5번째 카드 자리 — 비로그인 inline CTA -->
        <a
          v-if="showInlineCTA && idx === 3"
          class="inline-cta"
          role="button"
          tabindex="0"
          @click="goLogin"
          @keydown.enter="goLogin"
        >
          <i class="pi pi-user-plus inline-cta__icon" />
          <strong>로그인하면 맞춤 추천</strong>
          <small>코호트·관심종목 활용</small>
        </a>
      </template>
    </main>

    <!-- (c) 그리드 끝 큰 CTA -->
    <section v-if="showFooterCTA" class="footer-cta" aria-label="회원가입 안내">
      <div class="footer-cta__inner">
        <h2>나에게 맞는 추천을 받아보세요</h2>
        <p>로그인하면 코호트 매칭·관심종목 북마크 기능을 사용할 수 있습니다.</p>
        <button class="footer-cta__btn" @click="goLogin">로그인하기</button>
      </div>
    </section>

    <footer class="recommend-view__footer">
      <small>본 정보는 자문이 아닙니다.</small>
    </footer>
  </div>
</template>

<style scoped>
.recommend-view {
  max-width: var(--layout-max-width);
  margin: 0 auto;
  padding: var(--layout-content-pad);
  font-family: var(--font-sans);
  color: var(--text-primary);
  background: var(--surface-canvas);
}

.recommend-view__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-6) 0 var(--space-4);
  position: relative;
}
.recommend-view__title {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  line-height: var(--leading-tight);
  margin: 0;
}
.recommend-view__subtitle {
  display: flex; flex-wrap: wrap;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin: 0;
}
.recommend-view__dot { opacity: 0.5; }
.recommend-view__actions {
  position: absolute; top: var(--space-6); right: 0;
}
.recommend-view__toggle {
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.recommend-view__toggle:hover { background: var(--surface-muted); }
.recommend-view__toggle:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

/* 고급 옵션 */
.recommend-view__advanced {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}
.advanced-group { border: 0; padding: 0; margin: 0; }
.advanced-group legend {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}
.advanced-radio {
  display: inline-flex; align-items: center; gap: var(--space-2);
  margin-right: var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
}
.advanced-radio__warn {
  margin-left: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-warning);
}

/* Grid */
.recommend-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
  margin-top: var(--space-4);
}

/* Skeleton */
.skeleton-card {
  display: flex; flex-direction: column; gap: var(--space-2);
  padding: var(--card-recommend-padding);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  min-height: 180px;
}
.skeleton-line {
  height: 12px; border-radius: var(--radius-sm);
  background: linear-gradient(90deg,
    var(--surface-muted) 0%, var(--border-subtle) 50%, var(--surface-muted) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
}
.skeleton-line--sm { width: 30%; }
.skeleton-line--md { width: 60%; }
.skeleton-line--lg { width: 100%; height: 36px; }
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 에러·빈 상태 */
.recommend-view__error,
.recommend-view__empty {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-2);
  padding: var(--space-12);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  text-align: center;
}
.recommend-view__error i,
.recommend-view__empty i {
  font-size: 2rem; color: var(--text-tertiary);
}
.recommend-view__retry {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border: 0;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
}
.recommend-view__retry:hover { background: var(--color-primary-700); }

/* Inline CTA (b) — 5번째 카드 자리 */
.inline-cta {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-2);
  padding: var(--card-recommend-padding);
  background: var(--color-primary-50);
  border: 1px dashed var(--color-primary-300);
  border-radius: var(--radius-lg);
  color: var(--color-primary-700);
  cursor: pointer;
  min-height: 180px;
  text-align: center;
}
.inline-cta:hover { background: var(--color-primary-100); }
.inline-cta:focus-visible { outline: none; box-shadow: var(--shadow-focus); }
.inline-cta__icon { font-size: var(--text-2xl); }
.inline-cta small { font-size: var(--text-xs); opacity: 0.85; }

/* Footer CTA (c) — 그리드 끝 큰 영역 */
.footer-cta {
  margin: var(--layout-section-gap) 0 var(--space-6);
  background: linear-gradient(135deg,
    var(--color-primary-600), var(--color-primary-800));
  border-radius: var(--radius-xl);
  color: var(--text-inverse);
  padding: var(--space-10) var(--space-6);
}
.footer-cta__inner {
  max-width: 480px; margin: 0 auto; text-align: center;
  display: flex; flex-direction: column; gap: var(--space-3);
}
.footer-cta h2 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  margin: 0;
}
.footer-cta p {
  font-size: var(--text-base);
  opacity: 0.9;
  margin: 0;
}
.footer-cta__btn {
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-6);
  background: var(--surface-card);
  color: var(--color-primary-700);
  border: 0;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  cursor: pointer;
  align-self: center;
}

.recommend-view__footer {
  margin-top: var(--space-8);
  padding: var(--space-4) 0;
  text-align: center;
}
.recommend-view__footer small {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

/* 모바일 */
@media (max-width: 768px) {
  .recommend-view__actions { position: static; margin-top: var(--space-2); }
  .recommend-view__title   { font-size: var(--text-2xl); }
  .footer-cta              { padding: var(--space-6) var(--space-4); }
}
</style>

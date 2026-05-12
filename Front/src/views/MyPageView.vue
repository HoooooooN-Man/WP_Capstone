<script setup lang="ts">
// UX W5 C2 — MyPageView 재설계.
// 결정: PrimeVue Dialog (cohort 변경), avatar 이니셜, stats 2개 (가입일·관심종목 수),
//        로그아웃 footer, watchlist Top 3 미리보기.

import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Dialog from 'primevue/dialog'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import CohortCard from '@/components/CohortCard.vue'
import CohortPicker from '@/components/CohortPicker.vue'
import StatCard from '@/components/StatCard.vue'
import WatchlistItem from '@/components/WatchlistItem.vue'
import { deriveInitials, formatJoinedAt, useUserProfile } from '@/composables/useUserProfile'
import { useCohort } from '@/composables/useCohort'
import type { CohortKey } from '@/composables/useCohortMeta'

// @ts-ignore — 기존 stores
import { useAuthStore } from '@/stores/auth.js'
// @ts-ignore
import { useWatchlistStore } from '@/stores/watchlist'

const router = useRouter()
const auth   = useAuthStore()
const watch_ = useWatchlistStore()
const toast  = useToast()

const { profile }    = useUserProfile(auth)
const cohortApi      = useCohort()
const currentCohort  = cohortApi.value

const initials  = computed(() => deriveInitials(profile.value.name))
const joinedAt  = computed(() => formatJoinedAt(profile.value.joinedAt))

// Watchlist Top 3 미리보기
const watchTickers = computed<string[]>(() => (watch_.tickers ?? []) as string[])
const topPreview   = computed(() => watchTickers.value.slice(0, 3))

// cohort 변경 모달
const showCohortDialog = ref(false)
const draftCohort      = ref<CohortKey | null>(null)

function openCohortDialog() {
  draftCohort.value = (currentCohort.value as CohortKey | null) ?? null
  showCohortDialog.value = true
}

async function saveCohort() {
  if (!draftCohort.value) return
  try {
    await cohortApi.setCohort(draftCohort.value, { authenticated: auth.isAuthenticated })
    toast.add({
      severity: 'success',
      summary:  '관심사 변경됨',
      detail:   '추천이 새 관심사에 맞춰 갱신됩니다.',
      life:     3000,
    })
    showCohortDialog.value = false
  } catch (e) {
    toast.add({
      severity: 'error',
      summary:  '변경 실패',
      detail:   '잠시 후 다시 시도해주세요.',
      life:     3000,
    })
  }
}

function logout() {
  auth.logout?.()
  router.push('/')
}

function goWatchlist() { router.push('/watchlist') }
function goRecommend() { router.push('/recommend') }
function goStockDetail(ticker: string) { router.push(`/stock/${ticker}`) }
</script>

<template>
  <div class="mypage">
    <header class="mypage__header">
      <div class="mypage__avatar" aria-hidden="true">{{ initials }}</div>
      <div class="mypage__identity">
        <h1>{{ profile.name }}</h1>
        <span v-if="profile.email" class="mypage__email">{{ profile.email }}</span>
      </div>
    </header>

    <section class="mypage__section">
      <h2>내 관심사</h2>
      <CohortCard :cohort="currentCohort.value" @change="openCohortDialog" />
    </section>

    <section class="mypage__section">
      <div class="mypage__section-head">
        <h2>관심종목 ({{ watchTickers.length }})</h2>
        <a class="mypage__see-all" @click="goWatchlist" role="button" tabindex="0">전체 보기 →</a>
      </div>
      <ul v-if="topPreview.length" class="mypage__watch-preview">
        <WatchlistItem
          v-for="t in topPreview"
          :key="t"
          :ticker="t"
          :name="t"
          @click="goStockDetail(t)"
        />
      </ul>
      <div v-else class="mypage__empty">
        <p>관심종목이 없습니다.</p>
        <button class="mypage__cta" @click="goRecommend">추천에서 추가하기 →</button>
      </div>
    </section>

    <section class="mypage__section">
      <h2>활동 통계</h2>
      <div class="mypage__stats">
        <StatCard label="관심종목 수" :value="watchTickers.length" />
        <StatCard label="가입일" :value="joinedAt" />
      </div>
    </section>

    <footer class="mypage__footer">
      <button class="mypage__logout" @click="logout">로그아웃</button>
    </footer>

    <!-- Cohort 변경 모달 (PrimeVue Dialog) -->
    <Dialog
      v-model:visible="showCohortDialog"
      modal
      header="관심사 변경"
      :style="{ width: '480px' }"
      :breakpoints="{ '768px': '92vw' }"
      :draggable="false"
    >
      <CohortPicker v-model="draftCohort" name="mypage_cohort" />
      <template #footer>
        <button class="dialog-btn dialog-btn--ghost" @click="showCohortDialog = false">취소</button>
        <button
          class="dialog-btn dialog-btn--primary"
          :disabled="!draftCohort || draftCohort === currentCohort.value"
          @click="saveCohort"
        >
          저장
        </button>
      </template>
    </Dialog>

    <Toast position="bottom-center" />
  </div>
</template>

<style scoped>
.mypage {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--layout-content-pad);
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.mypage__header {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-6) 0 var(--space-4);
}
.mypage__avatar {
  width: 64px; height: 64px;
  border-radius: var(--radius-full);
  background: var(--color-primary-600);
  color: var(--text-inverse);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}
.mypage__identity h1 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}
.mypage__email {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.mypage__section {
  display: flex; flex-direction: column; gap: var(--space-3);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--border-subtle);
}
.mypage__section h2 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}
.mypage__section-head {
  display: flex; justify-content: space-between; align-items: center;
}
.mypage__see-all {
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  text-decoration: none;
  cursor: pointer;
}
.mypage__see-all:hover { text-decoration: underline; }

.mypage__watch-preview {
  list-style: none; padding: 0; margin: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.mypage__empty {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-4);
  background: var(--surface-muted);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
}
.mypage__cta {
  background: transparent;
  border: 0;
  color: var(--color-primary-600);
  cursor: pointer;
  font-family: inherit;
  font-size: var(--text-sm);
}
.mypage__cta:hover { text-decoration: underline; }

.mypage__stats {
  display: flex; gap: var(--space-3);
  flex-wrap: wrap;
}

.mypage__footer {
  padding: var(--space-6) 0;
  text-align: center;
}
.mypage__logout {
  padding: var(--space-2) var(--space-6);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;
}
.mypage__logout:hover { background: var(--surface-muted); }

/* Dialog footer buttons */
.dialog-btn {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  font-family: inherit;
  border: 1px solid var(--border-default);
}
.dialog-btn--ghost   { background: transparent; color: var(--text-secondary); }
.dialog-btn--primary {
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border-color: var(--color-primary-600);
}
.dialog-btn--primary:disabled {
  background: var(--color-neutral-300);
  border-color: var(--color-neutral-300);
  cursor: not-allowed;
}

/* UX W8B — 모바일 풀 대응 (≤768px). breakpoint 토큰 --bp-tablet 와 일치. */
@media (max-width: 768px) {
  .mypage {
    padding: var(--space-3);
  }
  .mypage__header {
    gap: var(--space-3);
    padding: var(--space-4) 0 var(--space-3);
  }
  .mypage__avatar {
    width: 48px; height: 48px;
    font-size: var(--text-lg);
  }
  .mypage__identity h1 {
    font-size: var(--text-xl);
  }
  .mypage__section {
    padding: var(--space-3) 0;
  }
  .mypage__section-head {
    flex-wrap: wrap; gap: var(--space-2);
  }
  .mypage__stats {
    gap: var(--space-2);
  }
}
</style>

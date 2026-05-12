<script setup lang="ts">
// UX W2 — 추천 메인 카드. 토스 벤치마크 (큰 점수 + tier 배지 + 북마크).
// 결정: 권고 일괄 수용 (tier D 노출·rank 표시·MetaBadge 카드 내 footer·클릭 동작).

import MetaBadge from './MetaBadge.vue'

type Tier = 'A' | 'B' | 'C' | 'D'

interface Props {
  ticker: string
  name: string
  sector?: string
  score: number
  tier: Tier
  rank?: number
  cohortMatch?: 'balanced' | 'growth' | 'dividend' | 'short_term' | 'beginner' | null
  diversify?: 'correlation' | 'sector' | 'embedding' | null
  isWatched?: boolean
}

interface Emits {
  (e: 'click'): void
  (e: 'watch-toggle'): void
}

const props = defineProps<Props>()
const emit  = defineEmits<Emits>()

const cohortLabel: Record<string, string> = {
  balanced: '균형', growth: '성장', dividend: '배당',
  short_term: '단타', beginner: '입문',
}
const diversifyLabel: Record<string, string> = {
  correlation: '상관', sector: '섹터', embedding: '임베딩',
}

function onWatch(ev: Event) {
  ev.stopPropagation()
  emit('watch-toggle')
}
</script>

<template>
  <article
    class="recommend-card"
    :data-tier="tier"
    role="button"
    tabindex="0"
    @click="emit('click')"
    @keydown.enter="emit('click')"
    @keydown.space.prevent="emit('click')"
  >
    <header class="recommend-card__header">
      <span class="recommend-card__tier" :data-tier="tier">{{ tier }}</span>
      <span class="recommend-card__ticker">{{ ticker }}</span>
      <button
        class="recommend-card__watch"
        :class="{ 'is-watched': isWatched }"
        :aria-label="isWatched ? '관심종목에서 제거' : '관심종목에 추가'"
        @click="onWatch"
      >
        <i :class="['pi', isWatched ? 'pi-bookmark-fill' : 'pi-bookmark']" />
      </button>
    </header>

    <div class="recommend-card__body">
      <h3 class="recommend-card__name">{{ name }}</h3>
      <span v-if="sector" class="recommend-card__sector">{{ sector }}</span>
      <div class="recommend-card__score-row">
        <span class="recommend-card__score">{{ score }}</span>
        <span class="recommend-card__score-unit">점</span>
        <span v-if="rank != null" class="recommend-card__rank">#{{ rank }}</span>
      </div>
    </div>

    <footer class="recommend-card__footer" v-if="cohortMatch || diversify">
      <MetaBadge
        v-if="cohortMatch"
        label="코호트"
        :value="cohortLabel[cohortMatch] ?? cohortMatch"
      />
      <MetaBadge
        v-if="diversify"
        label="다양성"
        :value="diversifyLabel[diversify] ?? diversify"
      />
    </footer>
  </article>
</template>

<style scoped>
.recommend-card {
  display: flex;
  flex-direction: column;
  gap: var(--card-recommend-gap);
  padding: var(--card-recommend-padding);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: box-shadow var(--duration-fast) var(--ease-out),
              transform   var(--duration-fast) var(--ease-out);
}
.recommend-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.recommend-card:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

.recommend-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.recommend-card__tier {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem; height: 1.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
}
.recommend-card__tier[data-tier='A'] { background: var(--tier-a-bg); color: var(--tier-a-text); }
.recommend-card__tier[data-tier='B'] { background: var(--tier-b-bg); color: var(--tier-b-text); }
.recommend-card__tier[data-tier='C'] { background: var(--tier-c-bg); color: var(--tier-c-text); }
.recommend-card__tier[data-tier='D'] {
  background: var(--color-neutral-200); color: var(--color-neutral-600);
}
.recommend-card__ticker { font-weight: var(--font-medium); }
.recommend-card__watch {
  margin-left: auto;
  background: transparent; border: 0; cursor: pointer;
  color: var(--text-tertiary);
  font-size: var(--text-lg);
  padding: var(--space-1);
}
.recommend-card__watch.is-watched { color: var(--color-primary-600); }

.recommend-card__body { display: flex; flex-direction: column; gap: var(--space-1); }
.recommend-card__name {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}
.recommend-card__sector { font-size: var(--text-sm); color: var(--text-secondary); }
.recommend-card__score-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.recommend-card__score {
  font-size: var(--score-large-size);
  font-weight: var(--score-large-weight);
  color: var(--text-primary);
  line-height: 1;
}
.recommend-card__score-unit {
  font-size: var(--text-base);
  color: var(--text-secondary);
}
.recommend-card__rank {
  margin-left: auto;
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.recommend-card__footer {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-subtle);
}
</style>

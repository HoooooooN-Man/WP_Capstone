<!--
  OnboardingModal.vue
  ===================
  UX W5 C3 — 스타일 다듬기 (로직 변경 없음).

  변경:
    - <dialog> + fixed div → PrimeVue <Dialog> (focus trap·ESC 자동).
    - 5번째 step 5 라디오 → CohortPicker 컴포넌트 (W5 C1) 재사용.
    - 색·간격 → design-tokens.css 변수 적용.
    - 캡스톤 시기 cohort 라벨 (conservative·value) → 차기 W2 백엔드 일치
      (balanced·growth·dividend·short_term·beginner). CohortPicker 가 정합.
    - "나중에 정할게요" = 5번째 step 의 "건너뛰기" 버튼 (chosenCohort=null finish).
-->
<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="false"
    :draggable="false"
    :style="{ width: '560px' }"
    :breakpoints="{ '768px': '92vw' }"
    class="onboarding-dialog"
    :aria-labelledby="titleId"
  >
    <template #header>
      <div class="onboarding__header">
        <div class="onboarding__step-counter" role="progressbar"
             :aria-valuenow="step" :aria-valuemin="1" :aria-valuemax="TOTAL_STEPS">
          <span
            v-for="i in TOTAL_STEPS"
            :key="i"
            class="onboarding__dot"
            :class="{ 'is-active': i === step, 'is-done': i < step }"
          />
        </div>
        <button
          class="onboarding__close"
          type="button"
          aria-label="투어 건너뛰기"
          @click="skip"
        >
          <i class="pi pi-times" aria-hidden="true" />
        </button>
      </div>
    </template>

    <div class="onboarding__body">
      <h2 :id="titleId" class="onboarding__title">{{ currentStep.title }}</h2>
      <p class="onboarding__text">{{ currentStep.body }}</p>

      <div v-if="currentStep.bullets" class="onboarding__bullets">
        <p v-for="(b, i) in currentStep.bullets" :key="i" class="onboarding__bullet">
          <i class="pi pi-check-circle" aria-hidden="true" /> {{ b }}
        </p>
      </div>

      <!-- 5번째 step — CohortPicker 재사용 -->
      <div v-if="currentStep.choose === 'cohort'" class="onboarding__cohort">
        <CohortPicker v-model="chosenCohort" name="onboarding_cohort" />
        <p class="onboarding__hint">
          "내 관심사 기반 정렬" — 본 정보는 자문이 아닙니다.
        </p>
      </div>
    </div>

    <template #footer>
      <div class="onboarding__actions">
        <button
          v-if="step > 1"
          type="button"
          class="onboarding__btn onboarding__btn--ghost"
          @click="step--"
        >이전</button>
        <span class="onboarding__spacer" />
        <button
          v-if="currentStep.choose === 'cohort'"
          type="button"
          class="onboarding__btn onboarding__btn--ghost"
          @click="finishWithoutCohort"
        >건너뛰기</button>
        <button
          v-if="step < TOTAL_STEPS"
          type="button"
          class="onboarding__btn onboarding__btn--primary"
          @click="step++"
        >다음</button>
        <button
          v-else
          type="button"
          class="onboarding__btn onboarding__btn--primary"
          :disabled="currentStep.choose === 'cohort' && !chosenCohort"
          @click="finish"
        >시작하기</button>
      </div>
      <p class="onboarding__footer-hint">
        <a href="/transparency" target="_blank" rel="noopener">
          모델 정직성 페이지에서 자세한 성능 지표 보기 →
        </a>
      </p>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import CohortPicker from '@/components/CohortPicker.vue'
import { useCohort } from '@/composables/useCohort'
import type { CohortKey } from '@/composables/useCohortMeta'

const STORAGE_KEY = 'onboarding_seen_v1'
const TOTAL_STEPS = 5

interface Step {
  title: string
  body: string
  bullets?: string[]
  choose?: 'cohort'
}

const STEPS: Step[] = [
  {
    title: 'AI 가 매일 종목을 점수로 평가합니다',
    body:
      'v9 ML 앙상블 모델(LightGBM·XGBoost·CatBoost)이 매일 KOSPI 종목을 1~100점으로 평가합니다. ' +
      '단순한 인기 추천이 아니라, 재무·모멘텀·외국인 수급·매크로 등 69개 피처를 종합한 결과입니다.',
  },
  {
    title: 'Tier 의 의미',
    body: 'Tier 는 일별 백분위 컷오프입니다. 추천 카드의 색상 배지가 그 종목의 위치를 보여줍니다.',
    bullets: [
      'Tier A — 상위 7% (최고 점수, 매수 후보)',
      'Tier B — 상위 8~20% (관심 추적)',
      'Tier C — 중위권 (관망)',
      'Tier D — 하위권 (회피·보유 시 검토)',
    ],
  },
  {
    title: '회원이 되면 매일의 변화를 놓치지 않습니다',
    body:
      '관심종목을 등록하면 다른 브라우저에서도 동기화되고, ' +
      'Tier 가 변하거나 점수가 임계값을 돌파하면 알림으로 받아볼 수 있습니다.',
    bullets: [
      '★ 관심종목 서버 저장',
      '🔔 Tier 변경 자동 알림',
      '📊 내 보유 종목의 건강진단 (섹터 편중·상관계수·VaR)',
    ],
  },
  {
    title: '우리는 성능을 정직하게 공개합니다',
    body:
      '학계 표준 방식대로 데이터를 Train·Validation·Holdout 으로 엄격 분리하고, ' +
      'Holdout 결과를 분기마다 단 한 번 공개합니다. ' +
      '모델의 알려진 한계도 모두 명시합니다.',
    bullets: [
      '/transparency 에서 분기별 holdout 성과 확인',
      'Deflated Sharpe 로 다중 검정 보정',
      '모든 추천에 SHAP 기반 자연어 이유 제공',
    ],
  },
  {
    title: '관심사 한 가지만 골라 주세요',
    body:
      '선택하신 관심사에 맞춰 종목 *정렬* 만 바뀝니다. 모델·점수는 동일하며, ' +
      '언제든 마이페이지에서 변경할 수 있습니다.',
    choose: 'cohort',
  },
]

const props = withDefaults(
  defineProps<{ forceShow?: boolean }>(),
  { forceShow: false },
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'finish'): void
}>()

const visible       = ref(false)
const step          = ref(1)
const titleId       = `onboarding-title-${Math.random().toString(36).slice(2, 8)}`
const chosenCohort  = ref<CohortKey | null>(null)
const { setCohort } = useCohort()
const currentStep   = computed(() => STEPS[step.value - 1])

onMounted(() => {
  if (props.forceShow) {
    visible.value = true
    return
  }
  try {
    if (localStorage.getItem(STORAGE_KEY) !== '1') {
      visible.value = true
    }
  } catch (e) {
    console.warn('[onboarding] localStorage unavailable', e)
  }
})

function _markSeen() {
  try { localStorage.setItem(STORAGE_KEY, '1') } catch (e) { /* ignore */ }
}

function skip() {
  _markSeen()
  visible.value = false
  emit('close')
}

async function finish() {
  if (chosenCohort.value) {
    try {
      // 차차차기 §3 권고: 건너뛰기 = balanced default. 명시 선택 시 그 값.
      await setCohort(chosenCohort.value, { authenticated: false })
    } catch (e) {
      console.error('[onboarding] cohort persist failed', e)
    }
  }
  _markSeen()
  visible.value = false
  emit('finish')
}

async function finishWithoutCohort() {
  try {
    // UX_사이클.md §3 — 건너뛰기 default = balanced.
    await setCohort('balanced', { authenticated: false })
  } catch (e) {
    console.error('[onboarding] default balanced 저장 실패', e)
  }
  _markSeen()
  visible.value = false
  emit('finish')
}
</script>

<style scoped>
.onboarding-dialog :deep(.p-dialog-header) {
  padding: var(--space-4) var(--space-5) 0;
  border: 0;
}
.onboarding-dialog :deep(.p-dialog-content) {
  padding: var(--space-4) var(--space-5);
  font-family: var(--font-sans);
}
.onboarding-dialog :deep(.p-dialog-footer) {
  padding: var(--space-3) var(--space-5) var(--space-5);
  border: 0;
}

/* Header */
.onboarding__header {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%;
}
.onboarding__step-counter {
  display: flex; gap: var(--space-2);
}
.onboarding__dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: var(--radius-full);
  background: var(--border-default);
  transition: background var(--duration-fast) var(--ease-out),
              width      var(--duration-fast) var(--ease-out);
}
.onboarding__dot.is-active {
  width: 24px;
  background: var(--color-primary-600);
}
.onboarding__dot.is-done {
  background: var(--color-primary-300);
}
.onboarding__close {
  background: transparent; border: 0;
  width: 32px; height: 32px;
  border-radius: var(--radius-full);
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: var(--text-base);
}
.onboarding__close:hover { background: var(--surface-muted); color: var(--text-primary); }

/* Body */
.onboarding__body { display: flex; flex-direction: column; gap: var(--space-3); }
.onboarding__title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: var(--leading-tight);
}
.onboarding__text {
  margin: 0;
  font-size: var(--text-base);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
}
.onboarding__bullets { display: flex; flex-direction: column; gap: var(--space-2); }
.onboarding__bullet {
  display: flex; align-items: flex-start; gap: var(--space-2);
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-primary);
}
.onboarding__bullet i { color: var(--color-primary-600); margin-top: 3px; }

.onboarding__cohort {
  display: flex; flex-direction: column; gap: var(--space-2);
  margin-top: var(--space-2);
}
.onboarding__hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin: 0;
}

/* Footer */
.onboarding__actions {
  display: flex; align-items: center;
  gap: var(--space-2);
}
.onboarding__spacer { flex: 1; }
.onboarding__btn {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  font-family: inherit;
  cursor: pointer;
  border: 1px solid var(--border-default);
}
.onboarding__btn--ghost {
  background: transparent;
  color: var(--text-secondary);
}
.onboarding__btn--ghost:hover { background: var(--surface-muted); }
.onboarding__btn--primary {
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border-color: var(--color-primary-600);
}
.onboarding__btn--primary:hover { background: var(--color-primary-700); }
.onboarding__btn--primary:disabled {
  background: var(--color-neutral-300);
  border-color: var(--color-neutral-300);
  cursor: not-allowed;
}

.onboarding__footer-hint {
  margin: var(--space-3) 0 0;
  text-align: center;
  font-size: var(--text-xs);
}
.onboarding__footer-hint a {
  color: var(--text-link); text-decoration: none;
}
.onboarding__footer-hint a:hover { text-decoration: underline; }
</style>

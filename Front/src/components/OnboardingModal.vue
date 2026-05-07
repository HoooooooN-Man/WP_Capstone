<!--
  OnboardingModal.vue
  ===================
  Tier 1.6 / 차별화 §3.5 — 신규 사용자 30초 가치 전달.

  4단계:
    1. 모델 소개   — v9 ML 앙상블이 매일 KOSPI 종목을 1~100점으로 평가
    2. Tier 의미   — A/B/C/D 컷오프와 백테스트 alpha 요약
    3. 회원 가치  — 관심종목·알림으로 매일 변화 추적
    4. 정직성     — Holdout 분리·Model Card 공개 (/transparency)

  사용 (App.vue 또는 main view):
    <OnboardingModal v-if="showOnboarding" @close="dismiss" />

  첫 방문 감지: localStorage 의 'onboarding_seen_v1' 키. 한 번 보면 다시 안 뜸.
-->
<template>
  <div v-if="visible" class="onboarding-backdrop" role="dialog" aria-modal="true" @click.self="skip">
    <div class="onboarding-modal" :aria-labelledby="titleId">
      <button
        class="close-btn"
        type="button"
        aria-label="투어 건너뛰기"
        @click="skip"
      >×</button>

      <div class="step-counter">
        <span
          v-for="i in TOTAL_STEPS"
          :key="i"
          class="dot"
          :class="{ active: i === step }"
        />
      </div>

      <h2 :id="titleId" class="step-title">{{ currentStep.title }}</h2>
      <p class="step-body">{{ currentStep.body }}</p>

      <div v-if="currentStep.bullets" class="step-bullets">
        <p v-for="(b, i) in currentStep.bullets" :key="i" class="bullet">
          <span class="bullet-mark">▸</span> {{ b }}
        </p>
      </div>

      <!-- W2: cohort 선택 step. step.choose === 'cohort' 일 때만 노출. -->
      <fieldset v-if="currentStep.choose === 'cohort'" class="cohort-form">
        <legend class="sr-only">관심사 선택</legend>
        <label
          v-for="opt in COHORT_OPTIONS"
          :key="opt.value ?? 'skip'"
          class="cohort-row"
          :class="{ active: chosenCohort === opt.value }"
        >
          <input
            type="radio"
            name="cohort"
            :value="opt.value"
            v-model="chosenCohort"
          />
          <span class="cohort-label">{{ opt.label }}</span>
          <span class="cohort-desc">{{ opt.desc }}</span>
        </label>
        <p class="form-hint">"내 관심사 기반 정렬" — 자문이 아닌 정보 정렬입니다.</p>
      </fieldset>

      <div class="actions">
        <button
          v-if="step > 1"
          type="button"
          class="btn-secondary"
          @click="step--"
        >이전</button>
        <button
          v-if="step < TOTAL_STEPS"
          type="button"
          class="btn-primary"
          @click="step++"
        >다음</button>
        <button
          v-else
          type="button"
          class="btn-primary"
          @click="finish"
        >시작하기</button>
      </div>

      <p class="footer-hint">
        <a href="/transparency" target="_blank" rel="noopener">
          모델 정직성 페이지에서 자세한 성능 지표 보기 →
        </a>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const STORAGE_KEY = 'onboarding_seen_v1'
const TOTAL_STEPS = 5

interface Step {
  title: string
  body: string
  bullets?: string[]
  /** W2 — cohort 선택 step 표시. 'cohort' 외에는 미표시. */
  choose?: 'cohort'
}

interface CohortOption {
  value: string | null
  label: string
  desc: string
}

const COHORT_OPTIONS: CohortOption[] = [
  { value: null,            label: '나중에 정할게요 (기본)',     desc: 'v9 점수 그대로 보여드립니다.' },
  { value: 'conservative',  label: '안정형',                     desc: '변동성 낮은 종목을 우선 보여드립니다.' },
  { value: 'balanced',      label: '균형형',                     desc: 'v9 점수 그대로 (기본과 동일).' },
  { value: 'growth',        label: '성장형',                     desc: '최근 모멘텀 강한 종목을 가중합니다.' },
  { value: 'dividend',      label: '배당 중심',                  desc: '배당수익률 2% 이상만 노출합니다.' },
  { value: 'value',         label: '가치 투자',                  desc: 'PER 15 미만 · PBR 1.5 미만 종목만 노출합니다.' },
]

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
  defineProps<{
    /** 부모가 강제로 보여주고 싶을 때 (개발 모드 등). */
    forceShow?: boolean
  }>(),
  { forceShow: false },
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'finish'): void
}>()

import { useCohort } from '@/composables/useCohort'

const visible = ref(false)
const step = ref(1)
const titleId = `onboarding-title-${Math.random().toString(36).slice(2, 8)}`
const chosenCohort = ref<string | null>(null)
const { setCohort } = useCohort()
const currentStep = computed(() => STEPS[step.value - 1])

onMounted(() => {
  if (props.forceShow) {
    visible.value = true
    return
  }
  // 첫 방문 감지.
  try {
    if (localStorage.getItem(STORAGE_KEY) !== '1') {
      visible.value = true
    }
  } catch (e) {
    // localStorage 에 접근 못 하는 환경(privacy mode 등) — 그냥 안 띄움.
    console.warn('[onboarding] localStorage unavailable', e)
  }
})

function skip() {
  _markSeen()
  visible.value = false
  emit('close')
}

async function finish() {
  // W2 — cohort 선택을 localStorage 즉시 저장. 로그인 상태면 서버에도 동시 PUT.
  // 인증 여부는 token 존재로만 판단 (auth store 의존 회피, 가벼운 판정).
  let authenticated = false
  try {
    const tok = localStorage.getItem('session_token')
    authenticated = !!tok
  } catch {
    /* ignore */
  }
  try {
    await setCohort(chosenCohort.value, { authenticated })
  } catch (e) {
    console.error('[onboarding] cohort persist failed', e)
  }
  _markSeen()
  visible.value = false
  emit('finish')
  emit('close')
}

function _markSeen() {
  try {
    localStorage.setItem(STORAGE_KEY, '1')
  } catch {
    /* ignore */
  }
}
</script>

<style scoped>
.onboarding-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.onboarding-modal {
  background: #fff;
  width: 100%;
  max-width: 480px;
  border-radius: 12px;
  padding: 28px 24px 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
  position: relative;
  font-family: inherit;
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 14px;
  background: transparent;
  border: 0;
  font-size: 22px;
  line-height: 1;
  color: #6b7280;
  cursor: pointer;
}
.close-btn:hover { color: #111827; }

.step-counter {
  display: flex;
  gap: 6px;
  margin-bottom: 14px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: #d1d5db;
}
.dot.active {
  background: #2563eb;
  width: 24px;
  transition: width 0.2s;
}

.step-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 10px;
  line-height: 1.3;
}
.step-body {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
  margin: 0 0 14px;
}

.step-bullets {
  background: #f9fafb;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 16px;
}

/* W2 — cohort 선택 form */
.cohort-form {
  border: 0;
  padding: 0;
  margin: 0 0 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cohort-row {
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: baseline;
  gap: 6px 10px;
  padding: 8px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: border-color 0.15s, background 0.15s;
}
.cohort-row:hover { background: #f9fafb; }
.cohort-row.active { border-color: #2563eb; background: #eff6ff; }
.cohort-row input[type="radio"] { margin: 0; }
.cohort-label { font-weight: 600; color: #111827; }
.cohort-desc  { color: #6b7280; font-size: 12px; }
.form-hint { font-size: 11px; color: #6b7280; margin: 4px 0 0; }
.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0;
  overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}
.bullet {
  margin: 4px 0;
  font-size: 13px;
  color: #1f2937;
  line-height: 1.5;
}
.bullet-mark {
  color: #2563eb;
  margin-right: 4px;
}

.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-bottom: 12px;
}
.btn-primary {
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 600;
  background: #2563eb;
  color: #fff;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}
.btn-primary:hover { background: #1d4ed8; }
.btn-secondary {
  padding: 8px 14px;
  font-size: 14px;
  background: #fff;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
}
.btn-secondary:hover { background: #f3f4f6; }

.footer-hint {
  text-align: center;
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}
.footer-hint a {
  color: #2563eb;
  text-decoration: none;
}
.footer-hint a:hover { text-decoration: underline; }
</style>

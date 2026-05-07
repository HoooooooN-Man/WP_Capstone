<!--
  ScoreWithConfidence.vue
  =======================
  Tier 1.4 (차별화 §2.1) — 점수와 앙상블 신뢰구간을 함께 표시.
  추천 카드의 점수 자리에 단순 숫자 대신 본 컴포넌트를 끼우면 차별화 시연이 즉시 가능.

  사용:
    <ScoreWithConfidence :score="73" :score-std="5" :disagreement="false" />

  → "73 ± 5" 표시. disagreement=true 면 "모델 의견 불일치" 배지 추가.
-->
<template>
  <div class="score-conf">
    <span class="score-main">{{ score.toFixed(1) }}</span>
    <span v-if="hasInterval" class="score-band">
      ± {{ scoreStd!.toFixed(1) }}
    </span>
    <span
      v-if="disagreement"
      class="disagree-badge"
      title="3개 모델(LightGBM·XGBoost·CatBoost) 의 예측이 평소보다 크게 벌어져 있습니다."
    >
      모델 불일치
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  score: number
  scoreStd?: number | null
  disagreement?: boolean | null
}>(), {
  scoreStd: null,
  disagreement: false,
})

const hasInterval = computed(
  () => props.scoreStd !== null && props.scoreStd !== undefined && props.scoreStd > 0,
)
</script>

<style scoped>
.score-conf {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
}

.score-main {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  font-variant-numeric: tabular-nums;
}

.score-band {
  font-size: 12px;
  color: #6b7280;
  font-variant-numeric: tabular-nums;
}

.disagree-badge {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 600;
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 9999px;
  letter-spacing: 0.02em;
}
</style>

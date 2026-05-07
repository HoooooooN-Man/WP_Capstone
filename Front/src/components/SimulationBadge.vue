<!--
  SimulationBadge.vue
  ===================
  Tier 1.7 (PRD §1.1) — 실시간 시세가 시뮬레이션임을 사용자에게 노란 배지로 표시.

  사용:
    <SimulationBadge v-if="isSimulation" />

  위치 권고: 종목 상세 차트 상단, 메인 페이지 시세 위젯 등 "현재가" 가 보이는 모든 곳.
-->
<template>
  <span
    role="status"
    aria-label="실시간 시세는 데모 시뮬레이션입니다"
    class="sim-badge"
    :title="title"
  >
    <span class="sim-dot" aria-hidden="true">●</span>
    {{ label }}
  </span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  label?: string
  title?: string
}>(), {
  label: '시뮬레이션',
  title: '실시간 시세는 종가 ±0.3% 의 데모 시뮬레이션입니다 (실거래 아님).',
})
</script>

<style scoped>
.sim-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
  color: #92400e;            /* amber-800 */
  background: #fef3c7;       /* amber-100 */
  border: 1px solid #f59e0b; /* amber-500 */
  border-radius: 9999px;
  letter-spacing: 0.02em;
}

.sim-dot {
  font-size: 9px;
  color: #d97706;            /* amber-600 */
}
</style>

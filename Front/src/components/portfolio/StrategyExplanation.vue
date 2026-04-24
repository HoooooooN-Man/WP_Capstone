<script setup>
defineProps({ type: { type: String, default: 'growth' } })
</script>

<template>
  <!-- 성장형 -->
  <div v-if="type === 'growth'" class="bg-gray-50 rounded-xl p-4">
    <p class="text-sm font-semibold text-gray-800 mb-1">성장형 전략</p>
    <p class="text-sm text-gray-500 leading-relaxed">
      ML 모델이 단기 상승 가능성이 높다고 판단한 KOSPI 상장 종목 Top 10입니다.<br>
      LightGBM · XGBoost · CatBoost 앙상블 점수를 기준으로 정렬했습니다.
    </p>
  </div>

  <!-- 안정형 -->
  <div v-else class="flex flex-col gap-3">
    <div class="bg-gray-50 rounded-xl p-4">
      <p class="text-sm font-semibold text-gray-800 mb-1">안정형 전략</p>
      <p class="text-sm text-gray-500 leading-relaxed">
        Tier A·B 종목 (ML점수 60점 이상) 중 최신 분기 PBR이 1.5 미만인 종목을 선별하여
        하방 리스크를 제한한 가치투자형 전략입니다.
      </p>
    </div>

    <div class="overflow-auto rounded-xl border border-gray-100">
      <table class="w-full text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="text-left text-xs text-gray-500 font-medium px-4 py-2.5">PBR 범위</th>
            <th class="text-left text-xs text-gray-500 font-medium px-4 py-2.5">해석</th>
          </tr>
        </thead>
        <tbody>
          <tr class="border-t border-gray-50">
            <td class="px-4 py-2 text-sm text-gray-700">&lt; 1.0</td>
            <td class="px-4 py-2 text-sm text-gray-500">극도 저평가 또는 구조적 문제</td>
          </tr>
          <tr class="border-t border-gray-50 bg-blue-50">
            <td class="px-4 py-2 text-sm text-blue-700 font-medium">1.0 ~ 1.5</td>
            <td class="px-4 py-2 text-sm text-blue-700 font-medium">안정적 저평가 · 현재 기준 ✓ 해당</td>
          </tr>
          <tr class="border-t border-gray-50">
            <td class="px-4 py-2 text-sm text-gray-700">1.5 ~ 3.0</td>
            <td class="px-4 py-2 text-sm text-gray-500">적정 수준</td>
          </tr>
          <tr class="border-t border-gray-50">
            <td class="px-4 py-2 text-sm text-gray-700">&gt; 3.0</td>
            <td class="px-4 py-2 text-sm text-gray-500">고평가 또는 성장 프리미엄</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

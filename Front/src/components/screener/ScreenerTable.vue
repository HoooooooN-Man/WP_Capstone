<script setup>
import { useRouter } from 'vue-router'
import TierBadge from '@/components/common/TierBadge.vue'

defineProps({
  items:   { type: Array,   default: () => [] },
  total:   { type: Number,  default: 0 },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
})
defineEmits(['reset-financial'])

const router = useRouter()

const TIER_COLORS = { A: '#1D9E75', B: '#378ADD', C: '#EF9F27', D: '#E24B4A' }

function barColor(score) {
  if (score >= 80) return TIER_COLORS.A
  if (score >= 60) return TIER_COLORS.B
  if (score >= 40) return TIER_COLORS.C
  return TIER_COLORS.D
}

function fmt(v, suffix = '') {
  return v != null ? v.toFixed(1) + suffix : '-'
}

function growthClass(v) {
  if (v == null) return 'text-gray-400'
  return v > 0 ? 'text-green-600' : v < 0 ? 'text-red-500' : 'text-gray-400'
}
</script>

<template>
  <div class="flex flex-col gap-3">

    <!-- 헤더 -->
    <p class="text-sm text-gray-500">총 <b class="text-gray-800">{{ total.toLocaleString() }}</b>개 종목</p>

    <!-- 로딩 -->
    <div v-if="loading" class="flex items-center justify-center h-48">
      <div class="w-6 h-6 border-2 border-gray-300 border-t-gray-700 rounded-full animate-spin" />
    </div>

    <!-- 에러 -->
    <div v-else-if="error" class="text-center text-gray-500 py-12">
      데이터를 불러오지 못했습니다
    </div>

    <!-- 빈 상태 -->
    <div v-else-if="!items.length" class="flex flex-col items-center py-12 gap-3">
      <p class="text-gray-500">조건에 맞는 종목이 없습니다</p>
      <button
        class="text-sm text-gray-500 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors"
        @click="$emit('reset-financial')"
      >
        조건 완화하기
      </button>
    </div>

    <!-- 테이블 -->
    <div v-else class="overflow-auto rounded-xl border border-gray-100 bg-white">
      <table class="w-full text-sm whitespace-nowrap">
        <thead class="bg-gray-50 sticky top-0">
          <tr>
            <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">순위</th>
            <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">종목명</th>
            <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">섹터</th>
            <!-- 복합점수 + 툴팁 -->
            <th class="text-left text-xs text-gray-500 font-medium px-3 py-2.5">
              <div class="relative group inline-flex items-center gap-1 cursor-help">
                복합점수 ⓘ
                <div class="absolute top-full left-0 mt-1 w-56 bg-gray-800 text-white text-xs rounded-lg p-2 hidden group-hover:block z-50 font-normal whitespace-normal leading-relaxed">
                  복합점수 = ML점수 × 0.6 + 재무점수 × 0.4<br>
                  재무 데이터 없는 종목은 재무점수 50 적용
                </div>
              </div>
            </th>
            <th class="text-right text-xs text-gray-500 font-medium px-3 py-2.5">ML점수</th>
            <th class="text-right text-xs text-gray-500 font-medium px-3 py-2.5">재무점수</th>
            <th class="text-right text-xs text-gray-500 font-medium px-3 py-2.5">PER</th>
            <th class="text-right text-xs text-gray-500 font-medium px-3 py-2.5">PBR</th>
            <th class="text-right text-xs text-gray-500 font-medium px-3 py-2.5">ROE</th>
            <th class="text-right text-xs text-gray-500 font-medium px-3 py-2.5">부채비율</th>
            <th class="text-right text-xs text-gray-500 font-medium px-3 py-2.5">영업이익률</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, idx) in items"
            :key="item.ticker"
            class="border-t border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
            @click="router.push('/stocks/' + item.ticker)"
          >
            <td class="px-3 py-2.5 text-xs text-gray-400">{{ idx + 1 }}</td>
            <td class="px-3 py-2.5">
              <div class="font-medium text-gray-900">{{ item.name }}</div>
              <div class="font-mono text-xs text-gray-400">{{ item.ticker }}</div>
            </td>
            <td class="px-3 py-2.5">
              <span class="bg-gray-100 text-gray-500 text-xs rounded-full px-2 py-0.5">{{ item.sector }}</span>
            </td>
            <!-- 복합점수 -->
            <td class="px-3 py-2.5">
              <div class="flex items-center gap-2">
                <div class="w-16 h-1.5 rounded bg-gray-200 overflow-hidden">
                  <div
                    class="h-full rounded"
                    :style="{ width: (item.composite_score ?? 0) + '%', backgroundColor: barColor(item.composite_score ?? 0) }"
                  />
                </div>
                <span class="text-sm font-medium">{{ Math.round(item.composite_score ?? 0) }}</span>
                <TierBadge :tier="item.tier" />
              </div>
            </td>
            <td class="px-3 py-2.5 text-right">{{ Math.round(item.score ?? 0) }}</td>
            <td class="px-3 py-2.5 text-right">
              <template v-if="item.finance_score != null">{{ item.finance_score.toFixed(1) }}</template>
              <template v-else><span class="text-gray-300">-</span> <span class="text-xs text-gray-300">(재무없음)</span></template>
            </td>
            <td class="px-3 py-2.5 text-right text-gray-600">{{ fmt(item.per) }}</td>
            <td class="px-3 py-2.5 text-right text-gray-600">{{ fmt(item.pbr) }}</td>
            <td class="px-3 py-2.5 text-right" :class="growthClass(item.roe)">{{ fmt(item.roe, '%') }}</td>
            <td class="px-3 py-2.5 text-right text-gray-600">{{ fmt(item.debt_ratio, '%') }}</td>
            <td class="px-3 py-2.5 text-right" :class="growthClass(item.op_margin)">{{ fmt(item.op_margin, '%') }}</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

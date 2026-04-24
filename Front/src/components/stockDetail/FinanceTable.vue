<script setup>
defineProps({ items: { type: Array, default: () => [] } })

function toEok(n) {
  if (!n) return '-'
  return (n / 1e8).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '억'
}
</script>

<template>
  <div class="overflow-auto rounded-xl border border-gray-100">
    <table class="w-full text-sm">
      <thead class="bg-gray-50 sticky top-0">
        <tr>
          <th class="text-left text-xs text-gray-500 font-medium px-4 py-2.5">연도/분기</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">매출</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">영업이익</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">당기순이익</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">EPS</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">매출성장률</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(item, idx) in items"
          :key="`${item.year}-${item.quarter}`"
          class="border-t border-gray-50 transition-colors"
          :class="idx === 0 ? 'bg-blue-50' : 'hover:bg-gray-50'"
        >
          <td class="px-4 py-2.5 font-medium text-gray-800">{{ item.year }}년 Q{{ item.quarter }}</td>
          <td class="px-4 py-2.5 text-right text-gray-600">{{ toEok(item.revenue) }}</td>
          <td class="px-4 py-2.5 text-right text-gray-600">{{ toEok(item.op_profit) }}</td>
          <td class="px-4 py-2.5 text-right text-gray-600">{{ toEok(item.net_profit) }}</td>
          <td class="px-4 py-2.5 text-right text-gray-600">{{ item.eps?.toLocaleString() ?? '-' }}원</td>
          <td
            class="px-4 py-2.5 text-right font-medium"
            :class="item.rev_growth_yoy > 0 ? 'text-green-600' : item.rev_growth_yoy < 0 ? 'text-red-500' : 'text-gray-400'"
          >
            {{ item.rev_growth_yoy != null ? item.rev_growth_yoy.toFixed(1) + '%' : '-' }}
          </td>
        </tr>
        <tr v-if="!items.length">
          <td colspan="6" class="text-center text-gray-400 py-8">재무 데이터 없음</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

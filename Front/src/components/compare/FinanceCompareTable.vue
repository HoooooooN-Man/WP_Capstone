<script setup>
defineProps({
  results:  { type: Array,  default: () => [] },
  colorMap: { type: Object, default: () => ({}) },
})

const METRICS = [
  { key: 'per',           label: 'PER',       unit: '배',  better: 'lower' },
  { key: 'pbr',           label: 'PBR',       unit: '배',  better: 'lower' },
  { key: 'roe',           label: 'ROE',       unit: '%',   better: 'higher' },
  { key: 'debt_ratio',    label: '부채비율',   unit: '%',   better: 'lower' },
  { key: 'op_margin',     label: '영업이익률', unit: '%',   better: 'higher' },
  { key: 'finance_score', label: '재무점수',   unit: '점',  better: 'higher' },
]

function getBestTicker(metricKey, better, results) {
  const vals = results
    .map(r => ({ ticker: r.ticker, val: r.finance?.[metricKey] }))
    .filter(v => v.val != null)
  if (!vals.length) return null
  return better === 'higher'
    ? vals.reduce((a, b) => a.val > b.val ? a : b).ticker
    : vals.reduce((a, b) => a.val < b.val ? a : b).ticker
}

function fmtVal(r, key, unit) {
  const v = r.finance?.[key]
  if (v == null) return null
  return Number.isInteger(v) ? v + unit : v.toFixed(1) + unit
}
</script>

<template>
  <div class="overflow-auto rounded-xl border border-gray-100 bg-white">
    <table class="w-full text-sm">
      <thead class="bg-gray-50 sticky top-0">
        <tr>
          <th class="text-left text-xs text-gray-500 font-medium px-4 py-2.5 w-32">지표</th>
          <th
            v-for="r in results"
            :key="r.ticker"
            class="text-right text-xs font-medium px-4 py-2.5 border-t-2"
            :style="{ borderTopColor: colorMap[r.ticker] }"
          >
            <div class="text-gray-800">{{ r.name }}</div>
            <div class="font-mono text-gray-400 font-normal">{{ r.ticker }}</div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="metric in METRICS"
          :key="metric.key"
          class="border-t border-gray-50"
        >
          <td class="px-4 py-2.5 text-gray-600 text-xs">{{ metric.label }}</td>
          <td
            v-for="r in results"
            :key="r.ticker"
            class="px-4 py-2.5 text-right text-sm rounded"
            :class="getBestTicker(metric.key, metric.better, results) === r.ticker
              ? 'bg-green-50 text-green-700 font-medium'
              : fmtVal(r, metric.key, metric.unit) == null
                ? 'text-gray-300'
                : 'text-gray-700'"
          >
            {{ fmtVal(r, metric.key, metric.unit) ?? '-' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

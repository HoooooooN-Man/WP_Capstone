<script setup>
defineProps({ summary: { type: Object, default: null } })

function valueClass(val) {
  if (!val) return 'text-gray-700'
  const str = String(val)
  if (str.startsWith('-')) return 'text-red-500 font-medium'
  if (str.includes('+') || (str.endsWith('%') && !str.startsWith('-'))) return 'text-green-600 font-medium'
  return 'text-gray-700'
}
</script>

<template>
  <div v-if="summary?.comparison" class="overflow-auto rounded-xl border border-gray-100">
    <table class="w-full text-sm">
      <thead class="bg-gray-50">
        <tr>
          <th class="text-left text-xs text-gray-500 font-medium px-4 py-2.5">지표명</th>
          <th class="text-right text-xs text-gray-500 font-medium px-4 py-2.5">값</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in summary.comparison"
          :key="row.key"
          class="border-t border-gray-50 hover:bg-gray-50"
        >
          <td class="px-4 py-2.5 text-gray-700">{{ row.key }}</td>
          <td class="px-4 py-2.5 text-right" :class="valueClass(row.value)">{{ row.value }}</td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else class="text-center text-gray-400 py-6 text-sm">백테스트 데이터 없음</div>
</template>

<script setup>
const props = defineProps({
  tier: { type: String, required: true },
})

const styles = {
  A: { background: '#E1F5EE', color: '#085041' },
  B: { background: '#E6F1FB', color: '#0C447C' },
  C: { background: '#FAEEDA', color: '#633806' },
  D: { background: '#F1EFE8', color: '#444441' },
}
</script>

<template>
  <span
    class="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-semibold leading-none"
    :style="styles[tier] ?? styles['D']"
  >
    {{ tier }}
  </span>
</template>

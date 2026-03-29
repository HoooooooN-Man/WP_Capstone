<template>
  <transition name="rise">
    <div v-if="visible" class="identity-card absolute top-0 left-1/2 -translate-x-1/2 w-72 h-40 bg-white rounded-xl shadow-2xl border border-slate-200 p-4 text-slate-800 transform-gpu">
      <div class="flex justify-between items-center">
        <span class="text-xs uppercase tracking-wider text-slate-500">ID Card</span>
        <LucideUserCircle class="text-slate-500" size="20" />
      </div>
      <h3 class="mt-2 text-lg font-bold">{{ name }}</h3>
      <p class="text-sm text-slate-500">투자 성향: {{ style }}</p>
      <p class="mt-1 text-base font-semibold">총 자산: {{ assets }}</p>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue';
import { LucideUserCircle } from 'lucide-vue-next';

const props = defineProps({
  name: { type: String, required: true },
  style: { type: String, required: true },
  assets: { type: String, required: true },
  visible: { type: Boolean, default: false },
});
</script>

<style scoped>
.rise-enter-from { transform: translateY(-40px) scale(0.92); opacity: 0; }
.rise-enter-active { transition: all 0.5s ease-out; }
.rise-enter-to { transform: translateY(0) scale(1); opacity: 1; }
.rise-leave-active { transition: all 0.35s ease-in; }
.rise-leave-to { transform: translateY(-20px) scale(0.98); opacity: 0; }
</style>
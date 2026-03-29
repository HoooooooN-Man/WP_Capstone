<template>
  <div class="portfolio-dock fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-slate-900/90 backdrop-blur-lg rounded-full px-4 py-2 flex items-center gap-4 shadow-2xl border border-slate-500/30">
    <button @click="$emit('wallet-click')" class="dock-item text-white p-2 rounded-full hover:bg-white/10 transition">
      <LucideWallet class="text-white" size="22" />
    </button>
    <button @click="$emit('portfolio-click')" class="dock-item text-white p-2 rounded-full hover:bg-white/10 transition">
      <LucideLayers class="text-white" size="22" />
    </button>
    <button @click="$emit('analysis-click')" class="dock-item text-white p-2 rounded-full hover:bg-white/10 transition">
      <LucideBarChart2 class="text-white" size="22" />
    </button>
    <button @click="$emit('user-click')" class="dock-item text-white p-2 rounded-full hover:bg-white/10 transition">
      <LucideUser class="text-white" size="22" />
    </button>
  </div>
</template>

<script setup>
import { LucideWallet, LucideLayers, LucideBarChart2, LucideUser } from 'lucide-vue-next';
</script>

<style scoped>
.portfolio-dock { min-width: 320px; }
.dock-item { width: 38px; height: 38px; display: flex; justify-content: center; align-items: center; }
</style>
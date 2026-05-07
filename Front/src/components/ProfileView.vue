<template>
  <div class="w-full h-full bg-[#fcfbf7] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.6)] p-12 lg:p-16 flex flex-col relative overflow-hidden animate-drop-in border border-black/10 text-gray-800">

    <div class="absolute -right-32 -bottom-32 opacity-[0.02] pointer-events-none z-0">
      <svg class="w-[800px] h-[800px]" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
    </div>

    <div class="flex justify-between items-center border-b-4 lg:border-b-8 border-gray-200 pb-8 z-10">
      <div class="flex flex-col gap-2">
        <h2 class="text-5xl lg:text-7xl font-black tracking-tighter uppercase text-[#2a170f]">Protector ID</h2>
        <span class="text-sm lg:text-xl font-bold text-gray-400 tracking-[0.5em] uppercase">Advanced Security Clearance • S-Tier Master</span>
      </div>
      <div class="px-8 py-4 bg-[#2a170f] rounded-2xl text-white text-3xl lg:text-5xl font-black tracking-widest shadow-xl rotate-[-5deg]">
        PASSED
      </div>
    </div>

    <div class="flex flex-1 gap-12 lg:gap-20 mt-10 z-10 overflow-hidden">
      <div class="w-1/3 max-w-[400px] flex flex-col gap-8 h-full">
        <div class="w-full aspect-[3/4] bg-gradient-to-br from-gray-100 to-gray-300 rounded-[2rem] shadow-inner flex items-center justify-center border-4 border-gray-200/50 relative overflow-hidden">
          <LucideUser class="w-48 h-48 lg:w-64 lg:h-64 text-gray-400/70" />
          <div class="absolute inset-0 bg-gradient-to-b from-transparent via-green-400/20 to-transparent animate-scan"></div>
        </div>
        <div class="w-full flex-1 min-h-[60px] opacity-40 flex flex-col justify-between p-2 bg-white rounded-xl border border-gray-200 shadow-inner">
          <div class="w-full h-full bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjcGF0dGVybikiIC8+PGRlZnM+PHBhdHRlcm4gaWQ9InBhdHRlcm4iIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHJlY3Qgd2lkdGg9IjIiIGhlaWdodD0iMjAiIGZpbGw9IiMwMDAiIC8+PHJlY3QgeD0iNCIgd2lkdGg9IjYiIGhlaWdodD0iMjAiIGZpbGw9IiMwMDAiIC8+PHJlY3QgeD0iMTQiIHdpZHRoPSI0IiBoZWlnaHQ9IjIwIiBmaWxsPSIjMDAwIiAvPjwvcGF0dGVybj48L2RlZnM+PC9zdmc+')]"></div>
        </div>
      </div>

      <div class="flex-1 flex flex-col justify-between py-4">
        <div>
          <p class="text-lg lg:text-xl text-gray-500 font-bold uppercase tracking-[0.3em] mb-2 lg:mb-4">Authorized Holder</p>
          <p class="text-6xl lg:text-[120px] font-black uppercase tracking-tighter text-[#1a0f0a] leading-none">{{ user.name || 'USER' }}</p>
          <div class="h-2 w-32 lg:w-48 bg-[#d9b9a9] mt-6 rounded-full"></div>
        </div>

        <div class="grid grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-10 lg:gap-y-16 border-t-4 lg:border-t-8 border-dashed border-gray-200 pt-10 lg:pt-16 mt-auto">
          <div class="flex flex-col gap-2">
            <p class="text-sm lg:text-base text-gray-400 font-bold uppercase tracking-widest">Invest Style</p>
            <p class="text-3xl lg:text-4xl font-extrabold text-gray-800">{{ user.style || '보수형' }}</p>
          </div>
          <div class="flex flex-col gap-2">
            <p class="text-sm lg:text-base text-gray-400 font-bold uppercase tracking-widest">Status</p>
            <p class="text-3xl lg:text-4xl font-extrabold text-green-600 flex items-center gap-3">
              <span class="w-4 h-4 lg:w-5 lg:h-5 rounded-full bg-green-500 animate-pulse"></span> ACTIVE
            </p>
          </div>
          <div class="flex flex-col gap-2 lg:col-span-1 col-span-2">
            <p class="text-sm lg:text-base text-gray-400 font-bold uppercase tracking-widest">Issue Date</p>
            <p class="text-3xl lg:text-4xl font-extrabold text-gray-800">2026. 04. 14</p>
          </div>
          <div class="flex flex-col gap-2 col-span-2 lg:col-span-3">
            <p class="text-sm lg:text-base text-gray-400 font-bold uppercase tracking-widest">Total Registered Assets</p>
            <p class="text-5xl lg:text-7xl font-black text-[#1a0f0a] tracking-tight">{{ user.totalAsset || '12,500,000 원' }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { LucideUser } from 'lucide-vue-next';

defineProps({
  user: {
    type: Object,
    required: true,
    default: () => ({ name: '', style: '', totalAsset: '' })
  }
});
</script>

<style scoped>
.animate-drop-in {
  animation: drop-in 0.7s var(--ease-wallet) forwards;
}

.animate-scan {
  animation: scan 3s linear infinite;
}
</style>
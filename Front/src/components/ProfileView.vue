<template>
  <div class="w-[540px] bg-[#fcfbf7] rounded-2xl shadow-[0_30px_60px_rgba(0,0,0,0.5)] p-8 flex flex-col relative overflow-hidden animate-drop-in border border-black/10 text-gray-800">
    
    <div class="absolute -right-10 -top-10 opacity-[0.03] pointer-events-none">
      <svg class="w-64 h-64" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
    </div>

    <div class="flex justify-between items-start border-b-2 border-gray-200 pb-4 mb-6 z-10">
      <div class="flex flex-col">
        <h2 class="text-2xl font-black tracking-widest uppercase text-[#2a170f]">Protector ID</h2>
        <span class="text-[10px] font-bold text-gray-400 tracking-[0.2em] mt-1">ADVANCED SECURITY CLEARANCE</span>
      </div>
      <div class="px-3 py-1 bg-[#2a170f] rounded-md text-white text-xs font-black tracking-widest">
        S-TIER
      </div>
    </div>

    <div class="flex gap-8 z-10">
      <div class="w-32 h-40 bg-gradient-to-b from-gray-200 to-gray-300 rounded-lg shadow-inner flex items-center justify-center border border-white/50 relative overflow-hidden">
        <LucideUser class="w-16 h-16 text-gray-400" />
      </div>

      <div class="flex flex-col justify-center space-y-4 flex-1">
        <div>
          <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-0.5">Authorized Name</p>
          <p class="text-2xl font-black uppercase tracking-tight text-[#1a0f0a]">{{ user.name || 'GUEST' }}</p>
        </div>
        
        <div class="flex gap-8">
          <div>
            <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-0.5">Invest Style</p>
            <p class="text-sm font-bold uppercase text-gray-700">{{ user.style || 'N/A' }}</p>
          </div>
          <div>
            <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-0.5">Status</p>
            <p class="text-sm font-bold uppercase text-green-600 flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> Active
            </p>
          </div>
        </div>

        <div>
          <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-0.5">Total Registered Assets</p>
          <p class="text-lg font-black text-[#1a0f0a]">{{ user.totalAsset || '0 KRW' }}</p>
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
@keyframes dropIn {
  0% { opacity: 0; transform: translateY(-40px) scale(0.95); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}

.animate-drop-in {
  animation: dropIn 0.7s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}
</style>
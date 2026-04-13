<template>
  <div class="card-wallet w-full min-h-screen flex flex-col items-center justify-end relative font-sans text-white overflow-hidden pb-0">
    
    <div class="absolute top-[10%] bottom-[140px] w-full max-w-[1100px] flex justify-center items-center z-0">
      <div class="animate-fade-in-delayed text-center">
        <h2 class="text-4xl font-black italic tracking-tighter text-white uppercase drop-shadow-lg">
          {{ activeCard === 'profile' ? (user.name || 'GUEST') + "'S SECURE VAULT" : activeCard.toUpperCase() + " SYSTEM" }}
        </h2>
        <div class="h-1 w-16 bg-[#d9b9a9] mt-4 opacity-70 rounded-full mx-auto"></div>
        <p class="mt-4 text-[#c9a999] tracking-[0.3em] uppercase text-[10px] font-bold">Module Active • {{ activeCard }}</p>
      </div>
    </div>

    <div class="relative z-10 w-full max-w-[1100px] h-[140px] bg-[#2a170f] rounded-t-[2.5rem] shadow-[0_-20px_60px_rgba(0,0,0,0.9)] border-t border-x border-white/5 flex animate-slide-up-wallet">
      
      <div class="absolute inset-0 opacity-50 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')] rounded-t-[2.5rem]"></div>
      
      <div class="absolute left-1/2 top-0 bottom-0 w-16 -translate-x-1/2 bg-gradient-to-r from-black/60 via-transparent to-black/60 pointer-events-none z-50"></div>
      <div class="absolute left-1/2 top-0 bottom-0 w-px -translate-x-1/2 bg-black/80 pointer-events-none z-50"></div>
      <div class="absolute left-1/2 top-0 bottom-0 w-[2px] ml-px -translate-x-1/2 bg-white/5 pointer-events-none z-50"></div>

      <div class="w-full h-full flex relative z-10">
        
        <div class="flex-1 flex flex-col items-center pt-10 gap-10">
          
          <div class="w-[75%] relative z-10">
            <div 
              @click="activeCard = 'profile'"
              class="absolute bottom-[2px] left-2 right-2 h-[50px] bg-gradient-to-br from-[#fcfbf7] to-[#e6e2d3] rounded-t-[10px] shadow-lg transition-transform duration-300 cursor-pointer flex items-center px-4 gap-3"
              :class="activeCard === 'profile' ? '-translate-y-6' : 'hover:-translate-y-6'"
            >
              <div class="w-7 h-7 rounded bg-black/5 flex items-center justify-center">
                <LucideUser class="w-4 h-4 text-black/60" />
              </div>
              <div class="flex flex-col justify-center">
                <span class="text-[13px] font-bold text-gray-800 leading-tight">{{ user.name || '주진우' }}</span>
                <span class="text-[9px] text-gray-500 font-medium leading-tight">Personal ID</span>
              </div>
            </div>
            <div class="w-full h-[3px] bg-[#120a07] border-b border-white/10 shadow-[inset_0_2px_4px_rgba(0,0,0,0.9)] rounded-full relative z-10 pointer-events-none"></div>
          </div>

          <div class="w-[75%] relative z-20">
            <div 
              @click="activeCard = 'feed'"
              class="absolute bottom-[2px] left-2 right-2 h-[50px] bg-gradient-to-br from-[#2edc68] to-[#1cb550] rounded-t-[10px] shadow-lg transition-transform duration-300 cursor-pointer flex items-center px-4 gap-2"
              :class="activeCard === 'feed' ? '-translate-y-6' : 'hover:-translate-y-6'"
            >
              <LucideSparkles class="w-5 h-5 text-white/90" />
              <span class="text-[15px] font-bold text-white tracking-wide">Latest Feed</span>
            </div>
            <div class="w-full h-[3px] bg-[#120a07] border-b border-white/10 shadow-[inset_0_2px_4px_rgba(0,0,0,0.9)] rounded-full relative z-10 pointer-events-none"></div>
          </div>
          
        </div>

        <div class="flex-1 flex flex-col items-center pt-10 gap-10">
          
          <div class="w-[75%] relative z-10">
            <div 
              @click="activeCard = 'company'"
              class="absolute bottom-[2px] left-2 right-2 h-[50px] bg-gradient-to-br from-[#1f3756] to-[#14253a] rounded-t-[10px] shadow-lg transition-transform duration-300 cursor-pointer flex items-center px-4 gap-2"
              :class="activeCard === 'company' ? '-translate-y-6' : 'hover:-translate-y-6'"
            >
              <LucideBuilding2 class="w-5 h-5 text-blue-200" />
              <span class="text-[15px] font-bold text-gray-100 tracking-wide">Company List</span>
            </div>
            <div class="w-full h-[3px] bg-[#120a07] border-b border-white/10 shadow-[inset_0_2px_4px_rgba(0,0,0,0.9)] rounded-full relative z-10 pointer-events-none"></div>
          </div>

          <div class="w-[75%] relative z-20">
            <div 
              @click="activeCard = 'portfolio'"
              class="absolute bottom-[2px] left-2 right-2 h-[50px] bg-gradient-to-br from-[#007ad9] to-[#0052a3] rounded-t-[10px] shadow-lg transition-transform duration-300 cursor-pointer flex items-center px-4 gap-2"
              :class="activeCard === 'portfolio' ? '-translate-y-6' : 'hover:-translate-y-6'"
            >
              <LucideFolder class="w-5 h-5 text-blue-100" />
              <span class="text-[15px] font-bold text-white tracking-wide">Portfolio</span>
            </div>
            <div class="w-full h-[3px] bg-[#120a07] border-b border-white/10 shadow-[inset_0_2px_4px_rgba(0,0,0,0.9)] rounded-full relative z-10 pointer-events-none"></div>
          </div>
          
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { LucideUser, LucideSparkles, LucideBuilding2, LucideFolder } from 'lucide-vue-next';

const props = defineProps({
  user: { 
    type: Object, 
    required: true,
    default: () => ({ name: '', style: '', totalAsset: '' })
  }
});

const emit = defineEmits(['toggle-wallet', 'toggle-portfolio']);

// 기본값을 'profile'(신분증)으로 설정하여 처음에 튀어나와 있도록 합니다.
const activeCard = ref('profile'); 

</script>

<style scoped>
/* 지갑 등장 애니메이션 */
@keyframes slideUpWallet {
  0% { transform: translateY(100%); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}

.animate-slide-up-wallet {
  animation: slideUpWallet 1s cubic-bezier(0.165, 0.84, 0.44, 1) forwards;
}

/* 상단 메인 화면 영역 페이드인 */
@keyframes fadeInDelayed {
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
}

.animate-fade-in-delayed {
  opacity: 0;
  animation: fadeInDelayed 1s cubic-bezier(0.165, 0.84, 0.44, 1) 0.5s forwards;
}
</style>
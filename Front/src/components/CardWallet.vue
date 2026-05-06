<template>
  <div class="card-wallet w-full min-h-screen flex flex-col items-center justify-end relative font-sans text-white overflow-hidden pb-0">

    <!-- 배경: AuthWallet과 동일 -->
    <div class="fixed inset-0 z-[-1] overflow-hidden bg-gradient-to-br from-[#0a0804] via-[#060402] to-[#0d0a05]">
      <div class="absolute w-[140vw] h-[80vh] bg-[#2a1e08] rounded-full blur-[160px] -top-[20vh] left-0 opacity-25"></div>
      <div class="absolute w-[100vw] h-[60vh] bg-[#1a1208] rounded-full blur-[120px] -bottom-[10vh] right-0 opacity-20"></div>
      <div class="absolute w-[60vw] h-[60vh] bg-[#3a2a0a] rounded-full blur-[100px] top-[20vh] right-[10vw] opacity-10"></div>
      <div class="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/30"></div>
    </div>

    <!-- 메인 컨텐츠 -->
    <div class="absolute top-[4%] bottom-[165px] left-[2%] right-[2%] flex justify-center items-center z-0">
      <transition name="fade-scale" mode="out-in">
        <ProfileView   v-if="activeCard === 'profile'"   :user="user" />
        <FeedView      v-else-if="activeCard === 'feed'" />
        <CompanyView   v-else-if="activeCard === 'company'"
          :replace-mode="replaceMode"
          @select-company="handleCompanySelect"
        />
        <PortfolioView v-else-if="activeCard === 'portfolio'"
          :portfolios="portfolios"
          @liquidate="handleLiquidate"
          @replace="handleReplace"
        />
        <div v-else class="text-center animate-fade-in-delayed">
          <h2 class="text-4xl font-black italic tracking-tighter text-white uppercase opacity-20">{{ activeCard }} MODULE STANDBY</h2>
        </div>
      </transition>
    </div>

    <!-- 지갑 바 -->
    <div
      class="wallet-bar relative z-10 w-full max-w-[1100px] rounded-t-[2.5rem] shadow-[0_-30px_80px_rgba(0,0,0,0.95)] border-t border-x border-white/5 flex animate-slide-up-wallet overflow-visible"
    >
      <!-- 가죽 질감 -->
      <div class="absolute inset-0 opacity-60 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')] rounded-t-[2.5rem] pointer-events-none"></div>

      <!-- 상단 봉제선 -->
      <div class="absolute top-3 left-4 right-4 border-t-2 border-dashed border-[#c9a227]/20 pointer-events-none z-20"></div>

      <!-- 중앙 분리선 -->
      <div class="absolute left-1/2 top-0 bottom-0 w-12 -translate-x-1/2 bg-gradient-to-r from-black/50 via-transparent to-black/50 pointer-events-none z-30"></div>
      <div class="absolute left-1/2 top-0 bottom-0 w-px -translate-x-1/2 bg-black/70 pointer-events-none z-30"></div>
      <div class="absolute left-1/2 top-0 bottom-0 w-px ml-px -translate-x-1/2 bg-white/5 pointer-events-none z-30"></div>

      <!-- 카드 슬롯 -->
      <div class="w-full h-full flex relative z-10">

        <!-- 왼쪽 열 -->
        <div class="flex-1 flex flex-col items-center pt-3 pb-3 gap-3">

          <!-- 슬롯 1: Profile -->
          <div class="w-[78%] flex-1 relative">
            <!-- 슬롯 배경 필러: 카드가 올라갈 때 지갑색으로 채워져 자연스럽게 보임 -->
            <div class="absolute inset-0 bg-[#2a1a0d] rounded-t-[10px]"></div>
            <!-- 카드 -->
            <div
              @click="activeCard = 'profile'"
              class="absolute inset-0 rounded-t-[10px] bg-gradient-to-br from-[#fcfbf7] to-[#e6e2d3] shadow-lg transition-transform duration-300 cursor-pointer flex items-center px-4 gap-3"
              :class="activeCard === 'profile' ? '-translate-y-4' : 'hover:-translate-y-4'"
            >
              <div class="w-7 h-7 rounded bg-black/5 flex items-center justify-center">
                <LucideUser class="w-4 h-4 text-black/60" />
              </div>
              <div class="flex flex-col justify-center">
                <span class="text-[13px] font-bold text-gray-800 leading-tight">{{ user.name || 'User' }}</span>
                <span class="text-[9px] text-gray-500 font-medium leading-tight">Personal ID</span>
              </div>
            </div>
            <!-- 슬롯 홈 라인 (카드 위에 올라와 홈 효과) -->
            <div class="absolute bottom-0 w-full h-[4px] bg-[#0b0704] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-10 pointer-events-none rounded-b-sm"></div>
          </div>

          <!-- 슬롯 2: Feed -->
          <div class="w-[78%] flex-1 relative">
            <div class="absolute inset-0 bg-[#1e1a0a] rounded-t-[10px]"></div>
            <div
              @click="activeCard = 'feed'"
              class="absolute inset-0 rounded-t-[10px] bg-gradient-to-br from-[#2edc68] to-[#1cb550] shadow-lg transition-transform duration-300 cursor-pointer flex items-center px-4 gap-2"
              :class="activeCard === 'feed' ? '-translate-y-4' : 'hover:-translate-y-4'"
            >
              <LucideSparkles class="w-5 h-5 text-white/90" />
              <span class="text-[15px] font-bold text-white tracking-wide">Latest Feed</span>
            </div>
            <div class="absolute bottom-0 w-full h-[4px] bg-[#0b0704] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-10 pointer-events-none rounded-b-sm"></div>
          </div>

        </div>

        <!-- 오른쪽 열 -->
        <div class="flex-1 flex flex-col items-center pt-3 pb-3 gap-3">

          <!-- 슬롯 3: Company -->
          <div class="w-[78%] flex-1 relative">
            <div class="absolute inset-0 bg-[#0e1520] rounded-t-[10px]"></div>
            <div
              @click="activeCard = 'company'"
              class="absolute inset-0 rounded-t-[10px] bg-gradient-to-br from-[#1f3756] to-[#14253a] shadow-lg transition-transform duration-300 cursor-pointer flex items-center px-4 gap-2"
              :class="activeCard === 'company' ? '-translate-y-4' : 'hover:-translate-y-4'"
            >
              <LucideBuilding2 class="w-5 h-5 text-blue-200" />
              <span class="text-[15px] font-bold text-gray-100 tracking-wide">Company List</span>
            </div>
            <div class="absolute bottom-0 w-full h-[4px] bg-[#0b0704] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-10 pointer-events-none rounded-b-sm"></div>
          </div>

          <!-- 슬롯 4: Portfolio -->
          <div class="w-[78%] flex-1 relative">
            <div class="absolute inset-0 bg-[#091422] rounded-t-[10px]"></div>
            <div
              @click="activeCard = 'portfolio'; $emit('toggle-portfolio')"
              class="absolute inset-0 rounded-t-[10px] bg-gradient-to-br from-[#007ad9] to-[#0052a3] shadow-lg transition-transform duration-300 cursor-pointer flex items-center px-4 gap-2"
              :class="activeCard === 'portfolio' ? '-translate-y-4' : 'hover:-translate-y-4'"
            >
              <LucideFolder class="w-5 h-5 text-blue-100" />
              <span class="text-[15px] font-bold text-white tracking-wide">Portfolio</span>
            </div>
            <div class="absolute bottom-0 w-full h-[4px] bg-[#0b0704] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-10 pointer-events-none rounded-b-sm"></div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { LucideUser, LucideSparkles, LucideBuilding2, LucideFolder } from 'lucide-vue-next';
import ProfileView   from './ProfileView.vue';
import FeedView      from './FeedView.vue';
import CompanyView   from './CompanyView.vue';
import PortfolioView from './PortfolioView.vue';

const props = defineProps({
  user: { type: Object, required: true, default: () => ({ name: '', style: '', totalAsset: '' }) }
});

const emit = defineEmits(['toggle-wallet', 'toggle-portfolio']);
const activeCard = ref('profile');

// 포트폴리오 데이터
const portfolios = ref([
  { id: 1, company: '삼성전자',       ticker: '005930', sector: '반도체', shares: 50, avgPrice: 68000,  currentPrice: 72400,  change:  6.47, color: '#1428A0', weight: 32 },
  { id: 2, company: 'SK하이닉스',    ticker: '000660', sector: '반도체', shares: 20, avgPrice: 145000, currentPrice: 158000, change:  8.97, color: '#BE0000', weight: 28 },
  { id: 3, company: 'NAVER',          ticker: '035420', sector: '인터넷', shares: 10, avgPrice: 180000, currentPrice: 172000, change: -4.44, color: '#03C75A', weight: 15 },
  { id: 4, company: 'LG에너지솔루션', ticker: '373220', sector: '배터리', shares:  5, avgPrice: 420000, currentPrice: 380000, change: -9.52, color: '#A50034', weight: 17 },
  { id: 5, company: 'Kakao',          ticker: '035720', sector: '인터넷', shares: 30, avgPrice: 52000,  currentPrice: 48500,  change: -6.73, color: '#3A1D1D', weight:  8 },
]);

// 교체 모드 상태
const replaceMode  = ref(false);
const replaceIndex = ref(-1);

const handleLiquidate = (index) => {
  portfolios.value.splice(index, 1);
};

const handleReplace = (index) => {
  replaceIndex.value = index;
  replaceMode.value  = true;
  activeCard.value   = 'company';
};

const handleCompanySelect = (company) => {
  if (replaceIndex.value >= 0) {
    portfolios.value.splice(replaceIndex.value, 1, company);
  }
  replaceMode.value  = false;
  replaceIndex.value = -1;
  activeCard.value   = 'portfolio';
};
</script>

<style scoped>
.wallet-bar {
  background: linear-gradient(to bottom, #3d2616, #2c1a0d 60%, #1e1009);
  height: 148px;
}

@keyframes slideUpWallet {
  0%   { transform: translateY(100%); opacity: 0; }
  75%  { transform: translateY(-2px);  opacity: 1; }
  100% { transform: translateY(10px);  opacity: 1; }
}

.animate-slide-up-wallet {
  animation: slideUpWallet 1s cubic-bezier(0.165, 0.84, 0.44, 1) forwards;
}

@keyframes fadeInDelayed {
  0%   { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
}

.animate-fade-in-delayed {
  opacity: 0;
  animation: fadeInDelayed 0.5s ease forwards;
}

.fade-scale-enter-active,
.fade-scale-leave-active  { transition: all 0.4s ease; }
.fade-scale-enter-from    { opacity: 0; transform: scale(0.95) translateY(10px); }
.fade-scale-leave-to      { opacity: 0; transform: scale(1.05) translateY(-10px); }
</style>

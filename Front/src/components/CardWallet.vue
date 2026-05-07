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
    <div class="absolute top-[4%] bottom-[100px] left-[2%] right-[2%] flex justify-center items-center z-0">
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

      <!-- 봉제선: 카드보다 아래 레이어 (z-[2]) -->
      <div class="absolute top-3 left-4 right-4 bottom-0 border-t-2 border-l-2 border-r-2 border-dashed border-[#c9a227]/20 rounded-t-[2rem] pointer-events-none z-[2]"></div>

      <!-- 중앙 분리선 -->
      <div class="absolute left-1/2 top-0 bottom-0 w-12 -translate-x-1/2 bg-gradient-to-r from-black/50 via-transparent to-black/50 pointer-events-none z-30"></div>
      <div class="absolute left-1/2 top-0 bottom-0 w-px -translate-x-1/2 bg-black/70 pointer-events-none z-30"></div>
      <div class="absolute left-1/2 top-0 bottom-0 w-px ml-px -translate-x-1/2 bg-white/5 pointer-events-none z-30"></div>

      <!-- 카드 슬롯 -->
      <div class="w-full h-full flex relative z-10">

        <!-- 왼쪽 열 -->
        <div class="flex-1 flex flex-col items-center pt-0 pb-2 gap-0">

          <!-- 슬롯 1: Profile (위 카드)
               홈 라인은 z-index 없음 → DOM 순서상 슬롯2 카드가 자연스럽게 위에 올라옴 -->
          <div class="w-[74%] flex-1 relative">
            <div
              @click="activeCard = 'profile'"
              class="absolute top-0 left-[3px] right-[3px] bottom-[0px] rounded-t-[10px] bg-gradient-to-br from-[#fcfbf7] to-[#e6e2d3] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-3"
              :class="activeCard === 'profile' ? '-translate-y-1' : 'hover:-translate-y-1'"
            >
              <div class="w-6 h-6 rounded bg-black/5 flex items-center justify-center flex-shrink-0">
                <LucideUser class="w-3.5 h-3.5 text-black/60" />
              </div>
              <div class="flex flex-col justify-center min-w-0">
                <span class="text-[12px] font-bold text-gray-800 leading-tight truncate">{{ user.name || 'User' }}</span>
                <span class="text-[9px] text-gray-500 font-medium leading-tight">Personal ID</span>
              </div>
            </div>
            <!-- 홈 라인: z-index 없음 (슬롯2 카드가 DOM 순서상 이 위에 올라옴) -->
            <div class="absolute bottom-[0px] w-full h-[4px] bg-[#0b0704] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] pointer-events-none rounded-b-sm"></div>
          </div>

          <!-- 슬롯 2: Feed (아래 카드 — DOM 순서상 슬롯1 홈 라인 위에 렌더링) -->
          <div class="w-[74%] flex-1 relative">
            <div
              @click="activeCard = 'feed'"
              class="absolute top-0 left-[3px] right-[3px] bottom-[0px] rounded-t-[10px] bg-gradient-to-br from-[#2edc68] to-[#1cb550] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2"
              :class="activeCard === 'feed' ? '-translate-y-2' : 'hover:-translate-y-2'"
            >
              <LucideSparkles class="w-4 h-4 text-white/90 flex-shrink-0" />
              <span class="text-[13px] font-bold text-white tracking-wide">Latest Feed</span>
            </div>
            <!-- 홈 아래 커버: 카드가 홈 아래로 보이지 않게 지갑 배경색으로 덮음 (z-[24] = 홈보다 아래) -->
            <div class="absolute bottom-0 left-0 right-0 h-[8px] pointer-events-none z-[24]" style="background: linear-gradient(to bottom, #231409, #1a0e07)"></div>
            <!-- 홈 라인: z-[25] → 슬롯2 카드 위에 표시 -->
            <div class="absolute bottom-[8px] w-full h-[4px] bg-[#0b0704] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-[25] pointer-events-none rounded-b-sm"></div>
          </div>

        </div>

        <!-- 오른쪽 열 (왼쪽과 동일한 레이어 구조) -->
        <div class="flex-1 flex flex-col items-center pt-0 pb-2 gap-0">

          <!-- 슬롯 3: Company (위 카드) -->
          <div class="w-[74%] flex-1 relative">
            <div
              @click="activeCard = 'company'"
              class="absolute top-0 left-[3px] right-[3px] bottom-[0px] rounded-t-[10px] bg-gradient-to-br from-[#1f3756] to-[#14253a] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2"
              :class="activeCard === 'company' ? '-translate-y-1' : 'hover:-translate-y-1'"
            >
              <LucideBuilding2 class="w-4 h-4 text-blue-200 flex-shrink-0" />
              <span class="text-[13px] font-bold text-gray-100 tracking-wide">Company List</span>
            </div>
            <!-- 홈 라인: z-index 없음 (슬롯4 카드가 위에 올라옴) -->
            <div class="absolute bottom-[0px] w-full h-[4px] bg-[#0b0704] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] pointer-events-none rounded-b-sm"></div>
          </div>

          <!-- 슬롯 4: Portfolio (아래 카드) -->
          <div class="w-[74%] flex-1 relative">
            <div
              @click="activeCard = 'portfolio'; $emit('toggle-portfolio')"
              class="absolute top-0 left-[3px] right-[3px] bottom-[0px] rounded-t-[10px] bg-gradient-to-br from-[#007ad9] to-[#0052a3] transition-transform duration-300 cursor-pointer flex items-center px-3 gap-2"
              :class="activeCard === 'portfolio' ? '-translate-y-2' : 'hover:-translate-y-2'"
            >
              <LucideFolder class="w-4 h-4 text-blue-100 flex-shrink-0" />
              <span class="text-[13px] font-bold text-white tracking-wide">Portfolio</span>
            </div>
            <!-- 홈 아래 커버: 카드가 홈 아래로 보이지 않게 지갑 배경색으로 덮음 (z-[24] = 홈보다 아래) -->
            <div class="absolute bottom-0 left-0 right-0 h-[8px] pointer-events-none z-[24]" style="background: linear-gradient(to bottom, #231409, #1a0e07)"></div>
            <!-- 홈 라인: z-[25] → 슬롯4 카드 위에 표시 -->
            <div class="absolute bottom-[8px] w-full h-[4px] bg-[#0b0704] shadow-[inset_0_3px_8px_rgba(0,0,0,1)] z-[25] pointer-events-none rounded-b-sm"></div>
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
  height: 100px;
}

.animate-slide-up-wallet {
  animation: slide-up-wallet 1s var(--ease-wallet) forwards;
}

.animate-fade-in-delayed {
  opacity: 0;
  animation: fade-in-delayed 0.5s ease forwards;
}
</style>

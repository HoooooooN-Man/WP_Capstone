<template>
  <div class="wallet-container min-h-screen flex flex-col items-center justify-center px-4 py-8 bg-[radial-gradient(circle_at_20%_20%,rgba(88,107,227,.28),transparent_54%)],radial-gradient(circle_at_80%_20%,rgba(60,191,255,.2),transparent_50%),#070809 text-white overflow-hidden">
    <div class="wallet-scene relative w-full max-w-[900px] h-[520px] flex items-center justify-center">
      <div class="wallet-3d-wrapper" :class="{ 'open': isOpen }">
        <div class="bifold-wallet">
          <div class="wallet-half wallet-left"></div>
          <div class="wallet-half wallet-right"></div>
          <div class="wallet-lock absolute inset-x-0 top-5 flex justify-center z-30">
            <LucideLock class="text-amber-300" :size="34" />
          </div>

          <div class="wallet-inside absolute inset-0 flex flex-col justify-between p-6 overflow-hidden">
            <div class="text-xs text-slate-300 font-medium tracking-widest">Smart Wallet / Bifold Meta</div>
            <div class="flex-1 flex items-center justify-center">
              <div class="glass-panel w-full max-w-md p-5 rounded-2xl border border-white/10 shadow-[0_30px_80px_rgba(0,0,0,0.6)] backdrop-blur-xl bg-slate-900/30">
                <h2 class="text-lg font-semibold text-white">Welcome, {{ user.name || 'Investor' }}</h2>
                <p class="text-sm text-slate-300 mt-1">투자 성향: {{ user.profile || 'Alpha 추구형' }}</p>
                <p class="text-xl font-bold mt-3 text-emerald-300">총 자산: {{ user.assets || '14,700,000원' }}</p>
              </div>
            </div>
            <div class="text-xs text-slate-400">지갑 내부 슬롯에서 ID 카드를 끌어올려보세요.</div>
          </div>

          <div class="id-card absolute inset-x-0 mx-auto w-[320px] h-[180px] rounded-3xl border border-amber-300/25 bg-gradient-to-br from-slate-800/95 to-slate-900/80 shadow-[0_16px_38px_rgba(16,24,40,0.7)] transform transition-all duration-700 ease-spring opacity-0 translate-y-8" :class="{ 'visible': isOpen }">
            <div class="p-5 h-full flex flex-col justify-between">
              <div>
                <div class="text-[0.65rem] uppercase tracking-widest text-amber-300">ID Card</div>
                <h3 class="text-2xl font-extrabold text-white mt-2">{{ user.name || '주진우' }}</h3>
                <p class="text-sm text-slate-300 mt-1">투자 성향: {{ user.profile || 'Alpha 추구형' }}</p>
              </div>
              <div class="pt-2 border-t border-white/10">
                <p class="text-xs text-slate-400">총 자산</p>
                <p class="text-2xl font-bold text-emerald-300">{{ user.assets || '15,300,000원' }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 지갑 반열기 상태 안내 -->
      <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-slate-300 w-fit px-3 py-2 rounded-full bg-black/30 backdrop-blur-sm">
        {{ isOpen ? '지갑이 열려있습니다. Dock에서 포트폴리오를 확인하세요.' : '지갑이 닫혀있습니다. 지갑 아이콘을 클릭하세요.' }}
      </div>
    </div>

    <!-- macOS 스타일 Dock -->
    <div class="mac-dock fixed bottom-6 left-1/2 -translate-x-1/2 w-[80%] max-w-[860px] flex items-center justify-center gap-4 p-2 rounded-3xl bg-white/10 backdrop-blur-2xl border border-white/15 shadow-[0_20px_45px_rgba(0,0,0,0.4)]">
      <button @click="$emit('toggle-wallet')" class="icon-btn" title="Wallet">
        <LucideWallet class="text-slate-100" :size="22" />
        <span>Wallet</span>
      </button>
      <button @click="$emit('toggle-portfolio')" class="icon-btn" title="Portfolio">
        <LucideLayers class="text-slate-100" :size="22" />
        <span>Portfolio</span>
      </button>
      <button class="icon-btn" title="Analytics">
        <LucideBarChart2 class="text-slate-100" :size="22" />
        <span>Analytics</span>
      </button>
      <button class="icon-btn" title="Settings">
        <LucideSettings class="text-slate-100" :size="22" />
        <span>Setting</span>
      </button>
    </div>

    <transition name="slide-up-fade">
      <div v-if="showPortfolio" class="w-full mt-10">
        <CardWallet />
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { LucideLock, LucideWallet, LucideLayers, LucideBarChart2, LucideSettings } from 'lucide-vue-next';
import CardWallet from './CardWallet.vue';

const props = defineProps({
  isOpen: { type: Boolean, required: true },
  user: { type: Object as () => { name: string; profile: string; assets: string }, required: true },
  showPortfolio: { type: Boolean, required: true },
});

const emit = defineEmits(['toggle-wallet', 'toggle-portfolio']);

</script>

<style scoped>
.wallet-3d-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1600px;
}

.bifold-wallet {
  width: 85%;
  max-width: 780px;
  height: 370px;
  border-radius: 38px;
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.8s cubic-bezier(0.17,0.84,0.44,1);
  transform: translateZ(-40px);
}

.wallet-half {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 50%;
  border-radius: 38px;
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
}

.wallet-left {
  left: 0;
  background: linear-gradient(115deg, #0f172a 15%, #131d2d 100%);
  transform-origin: 100% 50%;
  transform: rotateY(0deg);
  border-right: 1px solid rgba(255,255,255,0.08);
}

.wallet-right {
  right: 0;
  background: linear-gradient(305deg, #0c101b 15%, #111827 100%);
  transform-origin: 0 50%;
  transform: rotateY(0deg);
  border-left: 1px solid rgba(255,255,255,0.08);
}

.wallet-3d-wrapper.open .wallet-left {
  transform: rotateY(-78deg);
}

.wallet-3d-wrapper.open .wallet-right {
  transform: rotateY(78deg);
}

.wallet-lock {
  opacity: 1;
  transition: opacity 0.5s ease;
}

.wallet-3d-wrapper.open .wallet-lock {
  opacity: 0;
}

.id-card {
  transform: translateY(50px) scale(0.92);
  opacity: 0;
}

.id-card.visible {
  transform: translateY(-72px) scale(1);
  opacity: 1;
}

.glass-panel {
  transition: transform 0.4s ease, opacity 0.4s ease;
}

.wallet-3d-wrapper.open .glass-panel {
  transform: translateY(-8px);
}

.mac-dock {
  min-height: 76px;
}

.icon-btn {
  width: 87px;
  height: 58px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(14, 19, 32, 0.45);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  box-shadow: 0 12px 26px rgba(10, 14, 25, 0.45);
  transition: transform 0.2s ease, background 0.2s ease;
}

.icon-btn:hover {
  transform: translateY(-3px) scale(1.04);
  background: rgba(255,255,255,0.2);
}

.slide-up-fade-enter-from,
.slide-up-fade-leave-to {
  opacity: 0;
  transform: translateY(24px);
}

.slide-up-fade-enter-to,
.slide-up-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.slide-up-fade-enter-active,
.slide-up-fade-leave-active {
  transition: all 0.4s ease;
}
</style>

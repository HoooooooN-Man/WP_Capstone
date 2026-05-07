<template>
  <div class="auth-wallet min-h-screen w-full flex items-center justify-center relative font-sans perspective-container pl-4 pr-10 py-4">

    <!-- 배경: 다크골드 그라데이션 -->
    <div class="fixed inset-0 z-[-1] overflow-hidden bg-gradient-to-br from-[#0a0804] via-[#060402] to-[#0d0a05]">
      <div class="absolute w-[140vw] h-[80vh] bg-[#2a1e08] rounded-full blur-[160px] -top-[20vh] left-0 opacity-25"></div>
      <div class="absolute w-[100vw] h-[60vh] bg-[#1a1208] rounded-full blur-[120px] -bottom-[10vh] right-0 opacity-20"></div>
      <div class="absolute w-[60vw] h-[60vh] bg-[#3a2a0a] rounded-full blur-[100px] top-[20vh] right-[10vw] opacity-10"></div>
      <div class="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/30"></div>
    </div>

    <!-- 지갑 래퍼 -->
    <div
      class="relative z-10 w-full max-w-[600px] preserve-3d transition-transform duration-[1200ms] ease-in-out"
      style="height: clamp(380px, 55vh, 460px)"
      :class="{
        'translate-x-1/2': step === 2,
        'translate-x-1/2 translate-y-[120vh]': step >= 3
      }"
    >
      <!-- 지갑 두께감 (오른쪽 패널 — 뒷면의 좌우 대칭) -->
      <div class="absolute inset-0 bg-gradient-to-br from-[#2a1a0d] via-[#1e1209] to-[#261608] rounded-r-[2.5rem] shadow-[inset_-10px_0_30px_rgba(0,0,0,0.9)] border border-white/5 overflow-hidden">
        <div class="absolute inset-0 opacity-55 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
        <!-- 뒷면 봉제선의 좌우 대칭: 상+우+하, 왼쪽 없음 -->
        <div class="absolute top-4 right-4 bottom-4 left-0 border-t-2 border-r-2 border-b-2 border-dashed border-[#c9a227]/18 rounded-tr-[2rem] rounded-br-[2rem] pointer-events-none"></div>
      </div>

      <!-- 3D 플립 -->
      <div
        class="absolute inset-0 origin-left preserve-3d transition-transform duration-[1200ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
        :class="{'rotate-y-flip': step >= 2}"
      >
        <!-- ── 앞면 ── -->
        <div class="absolute inset-0 backface-hidden bg-gradient-to-br from-[#3d2616] via-[#2c1a0d] to-[#3a2210] rounded-r-[2.5rem] shadow-[30px_80px_150px_-20px_rgba(0,0,0,0.95)] border-t border-white/5">

          <!-- 가죽 질감 + 봉제선: overflow-hidden을 여기에만 적용해 자물쇠 버튼이 잘리지 않도록 -->
          <div class="absolute inset-0 rounded-r-[2.5rem] overflow-hidden pointer-events-none">
            <div class="absolute inset-0 opacity-65 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
            <div class="absolute left-0 inset-y-0 w-8 bg-gradient-to-r from-black/30 via-white/5 to-transparent z-10"></div>
            <div class="absolute left-0 inset-y-0 w-px bg-black/40"></div>
          </div>
          <!-- 봉제선: 상/우/하, 왼쪽 없음 — left-0으로 접히는 부분까지 연장 -->
          <div class="absolute top-4 right-4 bottom-4 left-0 border-t-2 border-r-2 border-b-2 border-dashed border-[#c9a227]/20 rounded-tr-[2rem] rounded-br-[2rem] pointer-events-none z-20"></div>

          <!-- 전체 컨텐츠: 세 블록을 하나로 묶어 세로 중앙 정렬 -->
          <div
            class="absolute inset-0 flex items-center justify-center z-20 transition-opacity duration-300"
            :class="{'opacity-0 pointer-events-none': step >= 1}"
          >
            <div class="flex flex-col items-center gap-5 w-full max-w-[320px] px-6">

              <!-- 타이틀 -->
              <div class="text-center w-full">
                <h1
                  class="font-black text-white tracking-tighter uppercase italic leading-none"
                  style="font-size: clamp(24px, 5vw, 38px); text-shadow: 0 2px 30px rgba(0,0,0,0.9), 0 0 50px rgba(100,75,15,0.25)"
                >WALLET PROTECTOR</h1>
                <div class="h-px w-16 bg-gradient-to-r from-transparent via-[#c9a227]/55 to-transparent mt-2.5 mx-auto"></div>
                <p class="text-[8px] text-[#9a7418] font-bold uppercase tracking-[0.35em] mt-1.5">Advanced Security Access</p>
              </div>

              <!-- 입력폼 -->
              <form @submit.prevent class="w-full space-y-2.5">
                <input v-model="email" type="email" placeholder="EMAIL ADDRESS" required
                  class="w-full px-4 py-3 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 focus:border-[#c9a227]/40 outline-none tracking-[0.18em] shadow-inner transition-colors" />
                <input v-model="password" type="password" placeholder="PASSWORD" required
                  class="w-full px-4 py-3 bg-black/50 border border-white/10 rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 focus:border-[#c9a227]/40 outline-none tracking-[0.18em] shadow-inner transition-colors" />
              </form>

              <!-- 소셜 로그인 -->
              <div class="flex flex-col items-center w-full">
                <div class="flex items-center gap-3 mb-3 w-full">
                  <div class="flex-1 h-px bg-gradient-to-r from-transparent to-white/10"></div>
                  <span class="text-[8px] text-[#7a5c20]/70 uppercase tracking-[0.3em] font-semibold">or</span>
                  <div class="flex-1 h-px bg-gradient-to-l from-transparent to-white/10"></div>
                </div>
                <div class="flex gap-3">
                  <!-- Google -->
                  <button type="button" class="w-9 h-9 rounded-full bg-black/40 border border-white/10 flex items-center justify-center hover:border-[#c9a227]/30 hover:bg-black/60 transition-all">
                    <img src="https://www.gstatic.com/images/branding/product/2x/googleg_48dp.png" class="w-[15px] h-[15px]" />
                  </button>
                  <!-- Naver -->
                  <button type="button" class="w-9 h-9 rounded-full bg-black/40 border border-white/10 flex items-center justify-center hover:border-[#c9a227]/30 hover:bg-black/60 transition-all">
                    <svg viewBox="0 0 24 24" fill="#03C75A" class="w-[15px] h-[15px]">
                      <path d="M15.5 12.4L8.5 3H6v18h3.5V8.6L16.5 18H19V3h-3.5z"/>
                    </svg>
                  </button>
                  <!-- Kakao -->
                  <button type="button" class="w-9 h-9 rounded-full bg-black/40 border border-white/10 flex items-center justify-center hover:border-[#c9a227]/30 hover:bg-black/60 transition-all">
                    <svg viewBox="0 0 24 24" fill="#FEE500" class="w-[16px] h-[16px]">
                      <path d="M12 3.5C6.75 3.5 2.5 7.05 2.5 11.45c0 2.76 1.8 5.2 4.54 6.64l-.96 3.97 4.28-2.6c.51.07 1.05.11 1.64.11 5.25 0 9.5-3.55 9.5-7.95S17.25 3.5 12 3.5z"/>
                    </svg>
                  </button>
                </div>
              </div>

            </div>
          </div>

          <!-- 자물쇠 버튼 -->
          <div
            @click="submitLogin"
            class="absolute -right-4 top-1/2 -translate-y-1/2 z-30 cursor-pointer group transition-opacity duration-300"
            :class="{'opacity-0 pointer-events-none': step >= 1}"
          >
            <div class="relative w-20 h-24 bg-[#2c1a0e] border-y border-l border-white/10 rounded-l-2xl shadow-[-10px_10px_20px_rgba(0,0,0,0.6)] overflow-hidden flex items-center">
              <div class="absolute inset-0 opacity-40 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
              <div class="relative w-16 h-16 ml-2 rounded-full bg-gradient-to-br from-[#e0c96a] to-[#a87820] border-4 border-[#2c1a0e] shadow-[0_0_20px_rgba(180,140,40,0.3)] flex items-center justify-center active:scale-90 transition-transform group-hover:brightness-110">
                <LucideLock class="w-6 h-6 text-[#1a0e04]" />
              </div>
            </div>
          </div>
        </div>

        <!-- ── 뒷면 ── -->
        <div class="absolute inset-0 backface-hidden rotate-y-180 bg-gradient-to-br from-[#2a1a0d] via-[#1e1209] to-[#261608] rounded-l-[2.5rem] shadow-inner border-t border-b border-l border-white/5 overflow-hidden">
          <div class="absolute inset-0 opacity-55 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
          <!-- 뒷면 봉제선: right-0으로 접히는 부분까지 연장 -->
          <div class="absolute top-4 left-4 bottom-4 right-0 border-t-2 border-l-2 border-b-2 border-dashed border-[#c9a227]/18 rounded-tl-[2rem] rounded-bl-[2rem] pointer-events-none"></div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { LucideLock } from 'lucide-vue-next';

const emit = defineEmits(['login']);
const email = ref('');
const password = ref('');
const step = ref(0);

const submitLogin = () => {
  if (step.value !== 0) return;

  step.value = 1;

  setTimeout(() => { step.value = 2; }, 300);
  setTimeout(() => { step.value = 3; }, 1700);
  setTimeout(() => {
    emit('login', { name: 'User', style: '보수형', totalAsset: '12,500,000원' });
  }, 2700);
};
</script>

<style scoped>
.perspective-container { perspective: 2000px; }
.preserve-3d { transform-style: preserve-3d; }
.backface-hidden { backface-visibility: hidden; }
.origin-left { transform-origin: left center; }
.rotate-y-180 { transform: rotateY(180deg); }
.rotate-y-flip { transform: rotateY(-180deg); }

input:focus {
  border-color: rgba(201, 162, 39, 0.4);
  box-shadow: inset 0 0 0 1px rgba(201, 162, 39, 0.08), 0 0 12px rgba(150, 110, 20, 0.12);
}
</style>

<template>
  <div class="auth-wallet min-h-screen w-full flex items-center justify-center relative font-sans perspective-container">
    
    <div class="fixed top-0 left-0 w-[100vw] h-[100vh] bg-[#050505] z-[-1] pointer-events-none overflow-hidden">
      <div class="absolute w-[150vw] h-[150vw] bg-[#4a3520] rounded-full blur-[120px] -top-[50vh] -left-[40vw] opacity-20"></div>
      <div class="absolute w-[120vw] h-[120vw] bg-[#1a1f1a] rounded-full blur-[100px] -bottom-[40vh] -right-[30vw] opacity-15"></div>
      <div class="absolute inset-0 bg-gradient-to-tr from-[#1a1a1a]/10 via-transparent to-[#3d2b1f]/10"></div>
      <div class="absolute inset-0 opacity-[0.02] bg-[url('https://www.transparenttextures.com/patterns/stardust.png')]"></div>
    </div>

    <div 
      class="relative z-10 w-full max-w-[640px] min-h-[440px] preserve-3d transition-transform duration-[1200ms] ease-in-out"
      :class="{
        'translate-x-1/2': step === 2,
        'translate-x-1/2 translate-y-[120vh]': step >= 3
      }"
    >
      
      <div class="absolute inset-0 bg-[#2a170f] rounded-r-[2.5rem] shadow-[inset_10px_0_30px_rgba(0,0,0,0.9)] overflow-hidden border border-white/5">
        <div class="absolute inset-0 opacity-50 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
      </div>

      <div 
        class="absolute inset-0 origin-left preserve-3d transition-transform duration-[1200ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
        :class="{'rotate-y-flip': step >= 2}"
      >
        <div class="absolute inset-0 backface-hidden bg-[#4a2e1e] rounded-r-[2.5rem] shadow-[30px_80px_150px_-20px_rgba(0,0,0,0.95)] border-t border-white/5 flex flex-col justify-center items-center py-10">
          
          <div class="absolute inset-0 rounded-r-[2.5rem] opacity-70 pointer-events-none mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
          <div class="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-black/20 via-white/5 to-transparent pointer-events-none z-10"></div>
          <div class="absolute left-0 top-0 bottom-0 w-px bg-black/30 pointer-events-none"></div>

          <div class="relative z-20 w-full max-w-[360px] flex flex-col items-center transition-opacity duration-300" :class="{'opacity-0 pointer-events-none': step >= 1}">
            
            <div class="text-center mb-8">
              <h1 class="text-5xl font-black text-white tracking-tighter uppercase italic drop-shadow-xl selection:bg-[#d9b9a9]/10">PROTECTOR</h1>
              <div class="h-1 w-20 bg-[#d9b9a9] mt-3 rounded-full opacity-60 mx-auto"></div>
              <p class="text-[10px] text-[#c9a999] font-bold uppercase tracking-[0.4em] mt-4 italic">Advanced Security Access</p>
            </div>

            <form @submit.prevent class="w-full space-y-4 mb-6">
              <input v-model="email" type="email" placeholder="EMAIL ADDRESS" required class="w-full px-6 py-4 bg-black/40 border border-white/5 rounded-2xl text-xs text-white placeholder:text-[#5c4033] focus:border-[#d9b9a9]/50 outline-none tracking-widest shadow-inner transition-colors" />
              <input v-model="password" type="password" placeholder="PASSWORD" required class="w-full px-6 py-4 bg-black/40 border border-white/5 rounded-2xl text-xs text-white placeholder:text-[#5c4033] focus:border-[#d9b9a9]/50 outline-none tracking-widest shadow-inner transition-colors" />
            </form>

            <div class="w-full text-center">
              <p class="text-[9px] text-[#c9a999] uppercase tracking-widest mb-3 italic opacity-60">or continue with:</p>
              <div class="flex justify-center gap-4">
                <button type="button" class="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-lg hover:scale-110 transition-transform"><img src="https://www.gstatic.com/images/branding/product/2x/googleg_48dp.png" class="w-5 h-5" /></button>
                <button type="button" class="w-10 h-10 rounded-full bg-[#24292f] flex items-center justify-center shadow-lg hover:scale-110 transition-transform text-white">
                  <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
                </button>
              </div>
            </div>
          </div>

          <div @click="submitLogin" class="absolute -right-4 top-1/2 -translate-y-1/2 flex items-center z-30 cursor-pointer group transition-opacity duration-300" :class="{'opacity-0 pointer-events-none': step >= 1}">
            <div class="relative w-20 h-24 bg-[#4a2e1e] border-y border-l border-white/10 rounded-l-2xl rounded-r-none shadow-[-10px_10px_20px_rgba(0,0,0,0.6)] overflow-hidden flex items-center">
              <div class="absolute inset-0 opacity-40 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
              <div class="relative w-16 h-16 ml-2 rounded-full bg-gradient-to-br from-gray-200 to-gray-500 border-4 border-[#4a2e1e] shadow-xl flex items-center justify-center active:scale-90 transition-transform group-hover:brightness-110">
                <LucideLock class="w-7 h-7 text-black drop-shadow-sm" />
              </div>
            </div>
          </div>
        </div>

        <div class="absolute inset-0 backface-hidden rotate-y-180 bg-[#3a2216] rounded-l-[2.5rem] shadow-inner border-t border-b border-l border-white/5 overflow-hidden">
          <div class="absolute inset-0 opacity-50 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
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

  // 1. 글자와 자물쇠 버튼이 스르륵 사라집니다. (0초)
  step.value = 1;
  
  // 2. 0.3초 뒤, 지갑이 열림과 동시에 지갑 전체가 오른쪽으로 이동하며 가운데 정렬을 맞춥니다.
  setTimeout(() => {
    step.value = 2;
  }, 300);

  // 3. 1.7초 뒤 (지갑이 완전히 열린 후 약간의 틈을 두고), 화면 밑으로 사라집니다.
  setTimeout(() => {
    step.value = 3;
  }, 1700);

  // 4. 2.7초 뒤, CardWallet으로 전환하라는 신호를 보냅니다.
  setTimeout(() => {
    emit('login', {
      name: '주진우',
      style: '보수형',
      totalAsset: '12,500,000원',
    });
  }, 2700); 
};
</script>

<style scoped>
/* 3D 연출 필수 요소 */
.perspective-container { perspective: 2000px; }
.preserve-3d { transform-style: preserve-3d; }
.backface-hidden { backface-visibility: hidden; }
.origin-left { transform-origin: left center; }
.rotate-y-180 { transform: rotateY(180deg); }
.rotate-y-flip { transform: rotateY(-180deg); }

input:focus {
  border-color: rgba(217, 185, 169, 0.5);
  box-shadow: 0 0 15px rgba(62, 43, 28, 0.3);
}
</style>
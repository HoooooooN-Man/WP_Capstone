<template>
  <div class="auth-wallet min-h-screen flex items-center justify-center bg-[#020617] p-6 relative overflow-hidden font-sans selection:bg-[#d9b9a9]/20 selection:text-white">
    <div class="absolute w-[800px] h-[800px] bg-blue-950/5 rounded-full blur-[140px] -top-1/4 -left-1/4 pointer-events-none"></div>
    <div class="absolute w-[800px] h-[800px] bg-indigo-950/5 rounded-full blur-[140px] -bottom-1/4 -right-1/4 pointer-events-none"></div>

    <div 
      class="relative z-10 w-full max-w-[560px] aspect-[1.7/1] bg-[#4a2e1e] rounded-[2.5rem] shadow-[0_80px_150px_-30px_rgba(0,0,0,0.95)] border-t border-white/5 transition-all duration-700 flex flex-col justify-between items-center overflow-visible ring-1 ring-white/5 py-12"
      :class="{'wallet-drop': isHolding}"
    >
      <div class="absolute inset-0 rounded-[2.5rem] opacity-70 pointer-events-none mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')]"></div>
      
      <div class="absolute inset-4.5 border-3 border-dashed border-white/10 rounded-[2rem] pointer-events-none z-0"></div>

      <div class="relative z-10 text-center">
        <h1 class="text-5xl font-black text-white tracking-tighter uppercase italic drop-shadow-xl selection:bg-[#d9b9a9]/10">
          PROTECTOR
        </h1>
        <div class="h-1 w-20 bg-[#d9b9a9] mt-3 rounded-full opacity-60 mx-auto"></div>
        <p class="text-[10px] text-[#c9a999] font-bold uppercase tracking-[0.4em] mt-4 italic">Advanced Security Access</p>
      </div>

      <form @submit.prevent class="relative z-10 space-y-3.5 w-full max-w-[320px]">
        <input 
          v-model="email"
          type="email" 
          placeholder="EMAIL ADDRESS" 
          required 
          class="w-full px-6 py-4.5 bg-black/40 border border-white/5 rounded-2xl text-xs text-white placeholder:text-[#5c4033] focus:border-[#d9b9a9]/50 focus:bg-black/60 outline-none transition-all tracking-widest shadow-inner" 
        />
        <input 
          v-model="password"
          type="password" 
          placeholder="PASSWORD" 
          required 
          class="w-full px-6 py-4.5 bg-black/40 border border-white/5 rounded-2xl text-xs text-white placeholder:text-[#5c4033] focus:border-[#d9b9a9]/50 focus:bg-black/60 outline-none transition-all tracking-widest shadow-inner" 
        />
      </form>

      <div class="relative z-10 w-full text-center pb-2">
        <p class="text-[9px] text-[#c9a999] uppercase tracking-widest mb-3 italic opacity-60">or continue with:</p>
        <div class="flex justify-center gap-4">
          <button type="button" class="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-lg hover:scale-110 transition-transform border border-white/10">
            <img src="https://www.gstatic.com/images/branding/product/2x/googleg_48dp.png" class="w-5 h-5" />
          </button>
          <button type="button" class="w-10 h-10 rounded-full bg-[#24292f] flex items-center justify-center shadow-lg hover:scale-110 transition-transform border border-white/10 text-white">
            <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
          </button>
        </div>
      </div>

      <div 
        @click="submitLogin"
        class="absolute -right-6 top-1/2 -translate-y-1/2 w-24 h-24 flex items-center justify-center z-20 cursor-pointer group"
      >
        <div class="absolute left-0 w-20 h-16 bg-[#4a2e1e] border border-white/5 rounded-r-2xl shadow-lg shadow-black/50 overflow-hidden ring-1 ring-white/5"></div>
        <div class="relative w-16 h-16 rounded-full bg-gradient-to-br from-gray-200 to-gray-500 border-4 border-[#4a2e1e] shadow-xl flex items-center justify-center active:scale-90 transition-transform">
          <LucideLock class="w-8 h-8 text-black drop-shadow-sm" />
        </div>
      </div>
    </div>

    <div 
      v-if="isHolding" 
      class="absolute bottom-0 left-0 w-full h-32 flex justify-center items-end gap-3 px-10 z-[50] animate-menu-up"
    >
      <div v-for="i in 4" :key="i" class="w-36 h-48 bg-gradient-to-br from-blue-700 to-indigo-900 rounded-2xl shadow-2xl border border-white/10 transform hover:-translate-y-12 transition-all cursor-pointer"></div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { LucideLock } from 'lucide-vue-next'; // 자물쇠 아이콘만 임포트

const emit = defineEmits(['login']);
const email = ref('');
const password = ref('');
const isHolding = ref(false); // [애니메이션 트리거]

const submitLogin = () => {
  if (!email.value || !password.value) return;
  
  // 1. 자물쇠를 누르면 지갑 하강 애니메이션 시작
  isHolding.value = true;
  
  // 2. [임시 딜레이] 지갑이 완전히 내려간 후 메인 화면으로 전환
  // 실제 로그인 로직은 부모 컴포넌트에서 처리하도록 이벤트를 보냅니다.
  setTimeout(() => {
    emit('login', {
      name: '주진우',
      style: '보수형',
      totalAsset: '12,500,000원',
    });
  }, 1000); // walletDrop 애니메이션 시간(1s)에 맞춤
};
</script>

<style scoped>
/* [2번 구현] 지갑 하강 애니메이션: 화면 아래에 살짝 걸치게 내려감 */
@keyframes walletDrop {
  0% { transform: perspective(1200px) translateY(0); opacity: 1; }
  100% { transform: perspective(1200px) translateY(85vh); opacity: 1; } /* 완전히 안 사라지고 바닥에 깔림 */
}
.wallet-drop {
  animation: walletDrop 1s forwards cubic-bezier(0.45, 0, 0.55, 1);
}

/* [3번 준비] 카드 메뉴바 등장 애니메이션 */
@keyframes menuUp {
  0% { transform: translateY(100%); }
  100% { transform: translateY(30px); }
}
.animate-menu-up {
  animation: menuUp 0.8s 0.5s forwards cubic-bezier(0.17, 0.67, 0.3, 1);
}
</style>
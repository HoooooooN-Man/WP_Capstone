<template>
  <div id="app" class="min-h-screen w-screen max-w-none m-0 bg-[#050505] text-slate-50 relative overflow-hidden font-sans selection:bg-[#d9b9a9]/30">
    
    <div class="fixed inset-0 w-full h-full pointer-events-none z-0">
      <div class="absolute w-[150vw] h-[150vw] bg-[#4a3520] rounded-full blur-[120px] -top-[50vh] -left-[40vw] opacity-20"></div>
      <div class="absolute w-[120vw] h-[120vw] bg-[#1a1f1a] rounded-full blur-[100px] -bottom-[40vh] -right-[30vw] opacity-15"></div>
      <div class="absolute inset-0 bg-gradient-to-tr from-[#1a1a1a]/10 via-transparent to-[#3d2b1f]/10"></div>
      <div class="absolute inset-0 opacity-[0.02] bg-[url('https://www.transparenttextures.com/patterns/stardust.png')]"></div>
    </div>

    <div class="relative z-10 w-full h-full min-h-screen flex items-center justify-center">
      
      <transition name="fade" mode="out-in">
        
        <AuthWallet 
          v-if="!isLoggedIn" 
          @login="handleLogin" 
        />

        <CardWallet 
          v-else
          :user="userInfo"
        />

      </transition>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import AuthWallet from './components/AuthWallet.vue'; 
import CardWallet from './components/CardWallet.vue'; 

// 상태 관리
const isLoggedIn = ref(false);
const userInfo = ref({ name: '', style: '', totalAsset: '' });

// AuthWallet에서 로그인 이벤트를 받았을 때 실행되는 함수
const handleLogin = (payload) => {
  // 1. 전달받은 유저 정보 저장
  userInfo.value = payload;

  // 2. 상태를 true로 변경하여 CardWallet 화면으로 전환
  isLoggedIn.value = true;
};
</script>

<style>
/* [가장 중요] Vue 프레임워크의 기본 여백 및 크기 제한을 완전히 박살냅니다. 
  이 코드가 있어야 양옆 레터박스나 스크롤바가 생기지 않습니다.
*/
html, body {
  margin: 0 !important;
  padding: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  overflow: hidden !important; /* 스크롤바 방지 */
  background-color: #050505;
}

#app { 
  width: 100vw !important; 
  min-height: 100vh !important; 
  max-width: 100% !important; 
  margin: 0 !important;
  padding: 0 !important;
}

/* [화면 전환 애니메이션 효과]
  로그인 창이 부드럽게 사라지고 메인 화면이 부드럽게 나타납니다.
*/
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.8s ease-in-out;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
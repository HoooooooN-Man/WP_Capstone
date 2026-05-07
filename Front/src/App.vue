<template>
  <div id="app">
    <transition name="fade" mode="out-in">
      <AuthWallet v-if="!isLoggedIn" @login="handleLogin" />
      <CardWallet v-else :user="userInfo" />
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue';

// [오류 해결!] 예전에 있던 LoginView, SignUpView import는 전부 지웠습니다.
// 오직 우리가 방금 만든 두 파일만 불러옵니다.
import AuthWallet from './components/AuthWallet.vue'; 
import CardWallet from './components/CardWallet.vue'; 

// 상태 관리
const isLoggedIn = ref(false);
const userInfo = ref({ name: '', style: '', totalAsset: '' });

// AuthWallet에서 로그인 이벤트를 받았을 때 실행
const handleLogin = (payload) => {
  userInfo.value = payload;
  isLoggedIn.value = true;
};
</script>


<template>
  <div id="app">
    <LoginView />
  </div>
</template>

<script setup>
// 윈도우 환경에서도 이 상대 경로가 가장 안전합니다.
import LoginView from './components/LoginView.vue'
</script>

<style>
/* 화면 여백 제거 */
body { margin: 0; padding: 0; overflow: hidden; }
</style>
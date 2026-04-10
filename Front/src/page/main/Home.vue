<template>
  <div class="home-container">
    <h1>Stock Analysis Platform</h1>
    
    <div v-if="authStore.isLoggedIn" class="user-info">
      <p>환영합니다, <strong>{{ authStore.user?.nickname }}</strong>님!</p>
      <div class="actions">
        <button @click="goToResetPassword">비밀번호 변경</button>
        <button @click="handleLogout" class="logout-btn">로그아웃</button>
      </div>
    </div>

    <div v-else class="guest-info">
      <p>서비스를 이용하려면 로그인이 필요합니다.</p>
      <button @click="$router.push('/login')">로그인하러 가기</button>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};

const goToResetPassword = () => {
  router.push('/reset-password');
};
</script>

<style scoped>
.home-container { padding: 20px; text-align: center; }
.user-info, .guest-info { margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }
.actions { display: flex; gap: 10px; justify-content: center; margin-top: 15px; }
.logout-btn { background-color: #ff4d4f; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.logout-btn:hover { background-color: #ff7875; }
</style>
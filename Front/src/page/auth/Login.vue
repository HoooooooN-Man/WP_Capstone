<template>
  <div class="max-w-md mx-auto mt-20 p-6 bg-white rounded shadow">
    <h2 class="text-2xl font-bold mb-6 text-center">로그인</h2>

    <form @submit.prevent="handleLogin">
      <div class="mb-4">
        <label class="block mb-1">이메일</label>
        <input v-model="email" type="email" class="border p-2 w-full rounded" required />
      </div>

      <div class="mb-6">
        <label class="block mb-1">비밀번호</label>
        <input v-model="password" type="password" class="border p-2 w-full rounded" required />
      </div>

      <button type="submit" class="w-full bg-indigo-600 text-white py-2 rounded font-bold">
        로그인
      </button>
    </form>

    <div class="mt-4 text-center text-sm text-gray-600">
      <router-link to="/register" class="text-blue-500">회원가입</router-link> | 
      <button @click="forgotPassword" class="text-gray-500">비밀번호를 잊으셨나요?</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import dbapi from '@/api/dbapi';
import { useRouter } from 'vue-router';

const router = useRouter();
const email = ref('');
const password = ref('');

const handleLogin = async () => {
  try {
    const response = await dbapi.post('/auth/login', {
      email: email.value,
      password: password.value
    });
    
    // 세션 토큰 및 유저 정보 저장
    localStorage.setItem('session_token', response.data.session_token);
    localStorage.setItem('nickname', response.data.nickname);
    
    alert(`${response.data.nickname}님 환영합니다!`);
    router.push('/home'); // 메인 페이지로 이동
  } catch (err) {
    alert(err.response?.data.detail || '로그인에 실패했습니다.');
  }
};

const forgotPassword = () => {
  // 비밀번호 재설정 페이지로 이동
  router.push('/reset-password');
};
</script>
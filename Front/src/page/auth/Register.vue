<template>
  <div class="max-w-md mx-auto mt-10 p-6 bg-white rounded shadow">
    <h2 class="text-2xl font-bold mb-6 text-center">회원가입</h2>

    <form @submit.prevent="handleRegister">
      <div class="mb-4">
        <label class="block mb-1">이메일</label>
        <div class="flex gap-2">
          <input v-model="form.email" type="email" class="border p-2 flex-1 rounded" :disabled="isEmailVerified" />
          <button @click.prevent="sendCode" :disabled="isEmailVerified" class="bg-blue-500 text-white px-3 py-1 rounded">
            코드발송
          </button>
        </div>
      </div>

      <div v-if="isCodeSent && !isEmailVerified" class="mb-4">
        <label class="block mb-1">인증코드</label>
        <div class="flex gap-2">
          <input v-model="form.code" type="text" class="border p-2 flex-1 rounded" placeholder="6자리 숫자" />
          <button @click.prevent="verifyCode" class="bg-green-500 text-white px-3 py-1 rounded">
            인증하기
          </button>
        </div>
      </div>

      <div class="mb-4">
        <label class="block mb-1">닉네임</label>
        <input v-model="form.nickname" type="text" class="border p-2 w-full rounded" />
      </div>

      <div class="mb-6">
        <label class="block mb-1">비밀번호</label>
        <input v-model="form.password" type="password" class="border p-2 w-full rounded" placeholder="영문, 숫자, 특수문자 포함 8-24자" />
      </div>

      <button type="submit" class="w-full bg-indigo-600 text-white py-2 rounded font-bold" :disabled="!isEmailVerified">
        가입하기
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import dbapi from '@/api/dbapi';
import { useRouter } from 'vue-router';

const router = useRouter();
const isCodeSent = ref(false);
const isEmailVerified = ref(false);

const form = reactive({
  email: '',
  code: '',
  nickname: '',
  password: ''
});

// 인증코드 발송
const sendCode = async () => {
  try {
    await dbapi.post(`/auth/check-email?email=${form.email}`);
    alert('인증 코드가 발송되었습니다.');
    isCodeSent.value = true;
  } catch (err) {
    alert(err.response?.data.detail || '발송 실패');
  }
};

// 인증코드 확인
const verifyCode = async () => {
  try {
    await dbapi.post('/auth/verify-code?purpose=register', {
      email: form.email,
      code: form.code
    });
    alert('이메일 인증에 성공했습니다.');
    isEmailVerified.value = true;
  } catch (err) {
    alert(err.response?.data.detail || '인증 실패');
  }
};

// 최종 가입
const handleRegister = async () => {
  try {
    await dbapi.post('/auth/register', {
      email: form.email,
      nickname: form.nickname,
      password: form.password
    });
    alert('회원가입이 완료되었습니다!');
    router.push('/login');
  } catch (err) {
    alert(err.response?.data.detail || '가입 실패');
  }
};
</script>
<template>
  <div class="max-w-md mx-auto mt-20 p-6 bg-white rounded shadow border">
    <h2 class="text-2xl font-bold mb-6 text-center">비밀번호 찾기</h2>

    <div v-if="step === 'verify'">
      <div class="mb-4">
        <label class="block mb-1 text-sm font-medium">가입한 이메일</label>
        <div class="flex gap-2">
          <input v-model="form.email" type="email" class="border p-2 flex-1 rounded" :disabled="isCodeSent" />
          <button @click="sendResetCode" :disabled="isCodeSent" class="bg-blue-600 text-white px-3 py-1 rounded text-sm">
            코드발송
          </button>
        </div>
      </div>

      <div v-if="isCodeSent" class="mb-6">
        <label class="block mb-1 text-sm font-medium">인증번호</label>
        <div class="flex gap-2">
          <input v-model="form.code" type="text" class="border p-2 flex-1 rounded" placeholder="6자리 숫자" />
          <button @click="verifyResetCode" class="bg-green-600 text-white px-3 py-1 rounded text-sm">
            인증확인
          </button>
        </div>
      </div>
    </div>

    <div v-else-if="step === 'new_password'">
      <div class="mb-4">
        <label class="block mb-1 text-sm font-medium">새 비밀번호</label>
        <input v-model="form.newPassword" type="password" class="border p-2 w-full rounded" placeholder="영문, 숫자, 특수문자 8-24자" />
      </div>
      <div class="mb-6">
        <label class="block mb-1 text-sm font-medium">비밀번호 확인</label>
        <input v-model="confirmPassword" type="password" class="border p-2 w-full rounded" />
      </div>
      <button @click="handlePasswordReset" class="w-full bg-indigo-600 text-white py-2 rounded font-bold">
        비밀번호 변경하기
      </button>
    </div>

    <div class="mt-4 text-center">
      <router-link to="/login" class="text-sm text-gray-500 hover:underline">로그인으로 돌아가기</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import dbapi from '@/api/dbapi'
import { useRouter } from 'vue-router'

const router = useRouter()
const step = ref('verify') // verify | new_password
const isCodeSent = ref(false)
const confirmPassword = ref('')

const form = reactive({
  email: '',
  code: '',
  newPassword: ''
})

// 1. 재설정 코드 발송
const sendResetCode = async () => {
  try {
    await dbapi.post(`/auth/send-reset-code?email=${form.email}`)
    alert('비밀번호 재설정을 위한 인증 코드가 발송되었습니다.')
    isCodeSent.value = true
  } catch (err) {
    alert(err.response?.data.detail || '이메일을 확인해주세요.')
  }
}

// 2. 인증코드 확인 (purpose=reset 필수)
const verifyResetCode = async () => {
  try {
    await dbapi.post('/auth/verify-code?purpose=reset', {
      email: form.email,
      code: form.code
    })
    alert('인증되었습니다. 새 비밀번호를 입력하세요.')
    step.value = 'new_password'
  } catch (err) {
    alert(err.response?.data.detail || '인증번호가 틀렸습니다.')
  }
}

// 3. 최종 비밀번호 변경
const handlePasswordReset = async () => {
  if (form.newPassword !== confirmPassword.value) {
    alert('비밀번호가 일치하지 않습니다.')
    return
  }

  try {
    await dbapi.post('/auth/reset-password-via-email', {
      email: form.email,
      code: form.code, // 백엔드 스키마에 따라 포함
      new_password: form.newPassword
    })
    alert('비밀번호가 성공적으로 변경되었습니다. 다시 로그인해주세요.')
    router.push('/login')
  } catch (err) {
    alert(err.response?.data.detail || '변경 실패')
  }
}
</script>
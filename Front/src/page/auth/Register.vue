<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme.js'
import dbapi from '@/api/dbapi'

const router = useRouter()
const theme  = useThemeStore()

const isCodeSent      = ref(false)
const isEmailVerified = ref(false)
const loading         = ref(false)
const error           = ref('')

const form = reactive({
  email:    '',
  code:     '',
  nickname: '',
  password: '',
})

// 인증코드 발송
const sendCode = async () => {
  error.value = ''
  loading.value = true
  try {
    await dbapi.post(`/auth/check-email?email=${form.email}`)
    isCodeSent.value = true
  } catch (err) {
    error.value = err.response?.data?.detail ?? '이메일 발송에 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// 인증코드 확인
const verifyCode = async () => {
  error.value = ''
  loading.value = true
  try {
    await dbapi.post('/auth/verify-code?purpose=register', {
      email: form.email,
      code:  form.code,
    })
    isEmailVerified.value = true
  } catch (err) {
    error.value = err.response?.data?.detail ?? '인증번호가 틀렸습니다.'
  } finally {
    loading.value = false
  }
}

// 최종 가입
const handleRegister = async () => {
  error.value = ''
  if (!isEmailVerified.value) { error.value = '이메일 인증을 먼저 완료하세요.'; return }
  loading.value = true
  try {
    await dbapi.post('/auth/register', {
      email:    form.email,
      nickname: form.nickname,
      password: form.password,
    })
    router.push('/login')
  } catch (err) {
    error.value = err.response?.data?.detail ?? '회원가입에 실패했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center px-4 py-8"
    :class="theme.isDark ? 'bg-[#0F1117]' : 'bg-[#F5F6F8]'"
  >
    <div
      class="w-full max-w-md rounded-2xl p-8 shadow-lg"
      :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white'"
    >
      <!-- 타이틀 -->
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold">회원가입</h1>
        <p class="text-sm mt-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
          WP_Capstone 계정 만들기
        </p>
      </div>

      <form @submit.prevent="handleRegister" class="space-y-4">

        <!-- 이메일 + 코드발송 -->
        <div>
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            이메일
          </label>
          <div class="flex gap-2">
            <input
              v-model="form.email"
              type="email"
              placeholder="example@email.com"
              :disabled="isEmailVerified"
              class="flex-1 rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors disabled:opacity-50"
              :class="theme.isDark
                ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
                : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400'"
            />
            <button
              type="button"
              :disabled="isEmailVerified || loading || !form.email"
              class="shrink-0 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
              :class="theme.isDark
                ? 'bg-white/10 text-gray-300 hover:bg-white/20 disabled:hover:bg-white/10'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:hover:bg-gray-100'"
              @click="sendCode"
            >
              {{ isCodeSent ? '재발송' : '코드 발송' }}
            </button>
          </div>
        </div>

        <!-- 인증코드 입력 -->
        <div v-if="isCodeSent && !isEmailVerified">
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            인증코드
          </label>
          <div class="flex gap-2">
            <input
              v-model="form.code"
              type="text"
              placeholder="6자리 숫자"
              maxlength="6"
              class="flex-1 rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
              :class="theme.isDark
                ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
                : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400'"
            />
            <button
              type="button"
              :disabled="loading || !form.code"
              class="shrink-0 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50 bg-green-600 text-white hover:bg-green-700"
              @click="verifyCode"
            >
              인증하기
            </button>
          </div>
        </div>

        <!-- 이메일 인증 완료 뱃지 -->
        <div
          v-if="isEmailVerified"
          class="flex items-center gap-2 text-sm px-4 py-2.5 rounded-xl"
          :class="theme.isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-50 text-green-700'"
        >
          ✅ 이메일 인증 완료
        </div>

        <!-- 닉네임 -->
        <div>
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">닉네임</label>
          <input
            v-model="form.nickname"
            type="text"
            placeholder="사용할 닉네임"
            required
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="theme.isDark
              ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
              : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400'"
          />
        </div>

        <!-- 비밀번호 -->
        <div>
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">비밀번호</label>
          <input
            v-model="form.password"
            type="password"
            placeholder="영문, 숫자, 특수문자 포함 8-24자"
            required
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="theme.isDark
              ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
              : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400'"
          />
        </div>

        <!-- 에러 -->
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>

        <!-- 제출 -->
        <button
          type="submit"
          :disabled="!isEmailVerified || loading"
          class="w-full py-2.5 rounded-xl font-semibold text-sm transition-colors mt-2 disabled:opacity-50"
          :class="loading
            ? 'bg-indigo-300 text-white cursor-not-allowed'
            : 'bg-indigo-600 text-white hover:bg-indigo-700'"
        >
          {{ loading ? '처리 중...' : '가입하기' }}
        </button>
      </form>

      <!-- 하단 -->
      <p class="text-center text-sm mt-6" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
        이미 계정이 있으신가요?
        <router-link
          to="/login"
          class="font-medium transition-colors"
          :class="theme.isDark ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-700'"
        >
          로그인
        </router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { useThemeStore } from '@/stores/theme.js'
import dbapi from '@/api/dbapi'

const router = useRouter()
const route  = useRoute()
const auth   = useAuthStore()
const theme  = useThemeStore()

const email    = ref('')
const password = ref('')
const loading  = ref(false)
const error    = ref('')

const handleLogin = async () => {
  error.value   = ''
  loading.value = true
  try {
    const { data } = await dbapi.post('/auth/login', {
      email: email.value,
      password: password.value,
    })
    // auth store + localStorage 동기화
    auth.login(data.session_token, data.nickname, data.user_id)

    // redirect 쿼리 있으면 해당 페이지로, 없으면 홈으로
    const redirect = route.query.redirect ?? '/'
    router.push(redirect)
  } catch (err) {
    error.value = err.response?.data?.detail ?? '로그인에 실패했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center px-4"
    :class="theme.isDark ? 'bg-[#0F1117]' : 'bg-[#F5F6F8]'"
  >
    <div
      class="w-full max-w-md rounded-2xl p-8 shadow-lg"
      :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white'"
    >
      <!-- 로고 -->
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold">WP_Capstone</h1>
        <p class="text-sm mt-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
          AI 주식 분석 서비스
        </p>
      </div>

      <!-- 폼 -->
      <form @submit.prevent="handleLogin" class="space-y-4">

        <!-- 이메일 -->
        <div>
          <label
            class="block text-sm font-medium mb-1.5"
            :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'"
          >이메일</label>
          <input
            v-model="email"
            type="email"
            placeholder="example@email.com"
            required
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="theme.isDark
              ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
              : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400'"
          />
        </div>

        <!-- 비밀번호 -->
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label
              class="text-sm font-medium"
              :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'"
            >비밀번호</label>
            <router-link
              to="/reset-password"
              class="text-xs transition-colors"
              :class="theme.isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'"
            >
              비밀번호를 잊으셨나요?
            </router-link>
          </div>
          <input
            v-model="password"
            type="password"
            placeholder="비밀번호 입력"
            required
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="theme.isDark
              ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
              : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400'"
          />
        </div>

        <!-- 에러 -->
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>

        <!-- 제출 버튼 -->
        <button
          type="submit"
          class="w-full py-2.5 rounded-xl font-semibold text-sm transition-colors mt-2"
          :class="loading
            ? (theme.isDark ? 'bg-indigo-800 text-indigo-400 cursor-not-allowed' : 'bg-indigo-300 text-white cursor-not-allowed')
            : 'bg-indigo-600 text-white hover:bg-indigo-700'"
          :disabled="loading"
        >
          {{ loading ? '로그인 중...' : '로그인' }}
        </button>
      </form>

      <!-- 하단 링크 -->
      <p class="text-center text-sm mt-6" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
        계정이 없으신가요?
        <router-link
          to="/register"
          class="font-medium transition-colors"
          :class="theme.isDark ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-700'"
        >
          회원가입
        </router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { useThemeStore } from '@/stores/theme.js'
import dbapi from '@/api/dbapi'
import SocialLoginButtons from '@/components/auth/SocialLoginButtons.vue'
import SetPasswordModal   from '@/components/auth/SetPasswordModal.vue'
import LinkConfirmModal   from '@/components/auth/LinkConfirmModal.vue'

const router = useRouter()
const route  = useRoute()
const auth   = useAuthStore()
const theme  = useThemeStore()

const email    = ref('')
const password = ref('')
const loading  = ref(false)
const error    = ref('')

// 모달 상태
const setPasswordModal  = ref({ show: false, nickname: '' })
const linkConfirmModal  = ref({ show: false, linkHintToken: '', provider: '' })

// ── 클라이언트 유효성 검사 ────────────────────────────────────────────────
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const emailError    = computed(() => email.value && !EMAIL_RE.test(email.value) ? '올바른 이메일 형식이 아닙니다.' : '')
const isFormValid   = computed(() => EMAIL_RE.test(email.value) && password.value.length >= 8)

// ── Open Redirect 방어 ───────────────────────────────────────────────────
function safeRedirect(raw) {
  if (!raw) return '/'
  // 같은 오리진의 상대경로만 허용 (/로 시작, //나 http로 시작하는 건 차단)
  if (/^\/(?!\/)/.test(raw)) return raw
  return '/'
}

// ── 로그인 제출 ──────────────────────────────────────────────────────────
const handleLogin = async () => {
  if (!isFormValid.value || loading.value) return
  error.value   = ''
  loading.value = true
  try {
    const { data } = await dbapi.post('/auth/login', {
      email:    email.value.trim().toLowerCase(),
      password: password.value,
    })
    auth.login(data.session_token, data.nickname, data.user_id)
    router.push(safeRedirect(route.query.redirect))
  } catch (err) {
    const status = err.response?.status
    if (status === 429) {
      error.value = '로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.'
    } else if (status === 401) {
      error.value = '이메일 또는 비밀번호가 올바르지 않습니다.'
    } else {
      error.value = err.response?.data?.detail ?? '로그인에 실패했습니다.'
    }
    // 보안: 실패 시 비밀번호 초기화
    password.value = ''
  } finally {
    loading.value = false
  }
}

// 소셜 로그인 후처리
const onSocialNeedsPassword = (token, nickname) => {
  setPasswordModal.value = { show: true, nickname }
}
const onSocialRequiresLinkConfirm = (linkHintToken, provider) => {
  linkConfirmModal.value = { show: true, linkHintToken, provider }
}
const onSocialDone = () => {
  router.push(safeRedirect(route.query.redirect))
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
      <form @submit.prevent="handleLogin" class="space-y-4" novalidate>

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
            autocomplete="email"
            required
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="[
              theme.isDark
                ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
                : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400',
              emailError ? 'border-red-500 focus:border-red-500' : ''
            ]"
          />
          <p v-if="emailError" class="text-red-500 text-xs mt-1">{{ emailError }}</p>
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
            autocomplete="current-password"
            required
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="theme.isDark
              ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
              : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400'"
          />
        </div>

        <!-- 에러 -->
        <p v-if="error" role="alert" class="text-red-500 text-sm">{{ error }}</p>

        <!-- 제출 버튼 -->
        <button
          type="submit"
          :disabled="!isFormValid || loading"
          class="w-full py-2.5 rounded-xl font-semibold text-sm transition-colors mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
          :class="loading
            ? (theme.isDark ? 'bg-indigo-800 text-indigo-400 cursor-not-allowed' : 'bg-indigo-300 text-white cursor-not-allowed')
            : 'bg-indigo-600 text-white hover:bg-indigo-700'"
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
    <!-- 모달 -->
  <SetPasswordModal
    v-if="setPasswordModal.show"
    :nickname="setPasswordModal.nickname"
    @close="setPasswordModal.show = false"
    @done="setPasswordModal.show = false"
  />
  <LinkConfirmModal
    v-if="linkConfirmModal.show"
    :link-hint-token="linkConfirmModal.linkHintToken"
    :provider="linkConfirmModal.provider"
    @close="linkConfirmModal.show = false"
  />
</template>
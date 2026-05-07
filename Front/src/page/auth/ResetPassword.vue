<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme.js'
import dbapi from '@/api/dbapi'

const router = useRouter()
const theme  = useThemeStore()

const step            = ref('verify')   // 'verify' | 'new_password'
const isCodeSent      = ref(false)
const loading         = ref(false)
const error           = ref('')
const confirmPassword = ref('')

const form = reactive({
  email:       '',
  code:        '',
  newPassword: '',
})

// ── 유효성 검사 ──────────────────────────────────────────────────────────
const EMAIL_RE    = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,24}$/

const emailError    = computed(() => form.email       && !EMAIL_RE.test(form.email)             ? '올바른 이메일 형식이 아닙니다.' : '')
const codeError     = computed(() => form.code        && !/^\d{6}$/.test(form.code)             ? '6자리 숫자를 입력해주세요.' : '')
const passwordError = computed(() => form.newPassword && !PASSWORD_RE.test(form.newPassword)    ? '8~24자, 영문과 숫자를 포함해야 합니다.' : '')
const confirmError  = computed(() => confirmPassword.value && form.newPassword !== confirmPassword.value ? '비밀번호가 일치하지 않습니다.' : '')

const canSendCode   = computed(() => EMAIL_RE.test(form.email) && !loading.value)
const canVerifyCode = computed(() => /^\d{6}$/.test(form.code) && !loading.value)
const isResetValid  = computed(() =>
  PASSWORD_RE.test(form.newPassword) &&
  form.newPassword === confirmPassword.value
)

// ── 재설정 코드 발송 ─────────────────────────────────────────────────────
const sendResetCode = async () => {
  if (!canSendCode.value) return
  error.value   = ''
  loading.value = true
  try {
    await dbapi.post(`/auth/check-email?email=${encodeURIComponent(form.email)}`)
    isCodeSent.value = true
    form.code = ''
  } catch (err) {
    const status = err.response?.status
    if (status === 429) {
      error.value = '잠시 후 다시 시도해주세요. (1분 제한)'
    } else {
      // 계정 존재 여부 노출 방지 — 서버 메시지 그대로 표시
      error.value = err.response?.data?.detail ?? '이메일을 확인해주세요.'
    }
  } finally {
    loading.value = false
  }
}

// ── 인증코드 확인 ────────────────────────────────────────────────────────
const verifyResetCode = async () => {
  if (!canVerifyCode.value) return
  error.value   = ''
  loading.value = true
  try {
    await dbapi.post('/auth/verify-code', {
      email: form.email,
      code:  form.code,
    })
    step.value = 'new_password'
  } catch (err) {
    const status = err.response?.status
    if (status === 429) {
      error.value = '인증 시도 횟수를 초과했습니다. 코드를 재발송 받아주세요.'
      isCodeSent.value = false
      form.code = ''
    } else {
      error.value = err.response?.data?.detail ?? '인증번호가 틀렸습니다.'
    }
  } finally {
    loading.value = false
  }
}

// ── 비밀번호 변경 ────────────────────────────────────────────────────────
const handlePasswordReset = async () => {
  if (!isResetValid.value || loading.value) return
  error.value   = ''
  loading.value = true
  try {
    await dbapi.post('/auth/reset-password-via-email', {
      email:        form.email.trim().toLowerCase(),
      new_password: form.newPassword,
    })
    router.push('/login')
  } catch (err) {
    error.value = err.response?.data?.detail ?? '변경에 실패했습니다.'
    // 보안: 실패 시 비밀번호 초기화
    form.newPassword  = ''
    confirmPassword.value = ''
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
      <!-- 타이틀 -->
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold">비밀번호 찾기</h1>
        <p class="text-sm mt-1" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
          가입한 이메일로 인증 후 변경
        </p>
      </div>

      <!-- 스텝 1: 이메일 인증 -->
      <div v-if="step === 'verify'" class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            가입한 이메일
          </label>
          <div class="flex gap-2">
            <input
              v-model="form.email"
              type="email"
              placeholder="example@email.com"
              autocomplete="email"
              :disabled="isCodeSent"
              class="flex-1 rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors disabled:opacity-50"
              :class="[
                theme.isDark
                  ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
                  : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400',
                emailError ? 'border-red-500 focus:border-red-500' : ''
              ]"
            />
            <button
              type="button"
              :disabled="!canSendCode"
              class="shrink-0 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
              :class="theme.isDark
                ? 'bg-white/10 text-gray-300 hover:bg-white/20'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
              @click="sendResetCode"
            >
              코드 발송
            </button>
          </div>
          <p v-if="emailError" class="text-red-500 text-xs mt-1">{{ emailError }}</p>
        </div>

        <div v-if="isCodeSent">
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            인증번호
          </label>
          <div class="flex gap-2">
            <input
              v-model="form.code"
              type="text"
              inputmode="numeric"
              placeholder="6자리 숫자"
              maxlength="6"
              class="flex-1 rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
              :class="[
                theme.isDark
                  ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
                  : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400',
                codeError ? 'border-red-500 focus:border-red-500' : ''
              ]"
            />
            <button
              type="button"
              :disabled="!canVerifyCode"
              class="shrink-0 px-4 py-2.5 rounded-xl text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50"
              @click="verifyResetCode"
            >
              인증확인
            </button>
          </div>
          <p v-if="codeError" class="text-red-500 text-xs mt-1">{{ codeError }}</p>
        </div>
      </div>

      <!-- 스텝 2: 새 비밀번호 입력 -->
      <div v-else-if="step === 'new_password'" class="space-y-4">
        <div
          class="flex items-center gap-2 text-sm px-4 py-2.5 rounded-xl mb-2"
          :class="theme.isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-50 text-green-700'"
        >
          ✅ 인증 완료. 새 비밀번호를 입력하세요.
        </div>

        <div>
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            새 비밀번호
          </label>
          <input
            v-model="form.newPassword"
            type="password"
            placeholder="영문, 숫자 포함 8~24자"
            autocomplete="new-password"
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="[
              theme.isDark
                ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
                : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400',
              passwordError ? 'border-red-500 focus:border-red-500' : ''
            ]"
          />
          <p v-if="passwordError" class="text-red-500 text-xs mt-1">{{ passwordError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            비밀번호 확인
          </label>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="비밀번호 재입력"
            autocomplete="new-password"
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="[
              theme.isDark
                ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
                : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400',
              confirmError ? 'border-red-500 focus:border-red-500' : ''
            ]"
          />
          <p v-if="confirmError" class="text-red-500 text-xs mt-1">{{ confirmError }}</p>
        </div>

        <button
          type="button"
          :disabled="!isResetValid || loading"
          class="w-full py-2.5 rounded-xl font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-indigo-600 text-white hover:bg-indigo-700"
          @click="handlePasswordReset"
        >
          {{ loading ? '변경 중...' : '비밀번호 변경하기' }}
        </button>
      </div>

      <!-- 에러 -->
      <p v-if="error" role="alert" class="text-red-500 text-sm mt-3">{{ error }}</p>

      <!-- 로그인으로 돌아가기 -->
      <div class="mt-6 text-center">
        <router-link
          to="/login"
          class="text-sm transition-colors"
          :class="theme.isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'"
        >
          ← 로그인으로 돌아가기
        </router-link>
      </div>
    </div>
  </div>
</template>
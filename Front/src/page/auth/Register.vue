<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme.js'
import dbapi from '@/api/dbapi'
import SocialLoginButtons from '@/components/auth/SocialLoginButtons.vue'
import SetPasswordModal   from '@/components/auth/SetPasswordModal.vue'
import LinkConfirmModal   from '@/components/auth/LinkConfirmModal.vue'

const router = useRouter()
const theme  = useThemeStore()

const isCodeSent      = ref(false)
const isEmailVerified = ref(false)
const loading         = ref(false)
const error           = ref('')

const setPasswordModal = ref({ show: false, nickname: '' })
const linkConfirmModal = ref({ show: false, linkHintToken: '', provider: '' })

const onSocialNeedsPassword       = (token, nickname) => { setPasswordModal.value = { show: true, nickname } }
const onSocialRequiresLinkConfirm = (linkHintToken, provider) => { linkConfirmModal.value = { show: true, linkHintToken, provider } }
const onSocialDone = () => router.push('/')

const form = reactive({
  email:    '',
  code:     '',
  nickname: '',
  password: '',
})
const confirmPassword = ref('')

// ── 유효성 검사 ──────────────────────────────────────────────────────────
const EMAIL_RE    = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const NICKNAME_RE = /^[가-힣a-zA-Z0-9_]{2,20}$/
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,24}$/

const emailError    = computed(() => form.email    && !EMAIL_RE.test(form.email)       ? '올바른 이메일 형식이 아닙니다.' : '')
const nicknameError = computed(() => form.nickname && !NICKNAME_RE.test(form.nickname) ? '2~20자, 한글/영문/숫자/_만 사용 가능합니다.' : '')
const passwordError = computed(() => form.password && !PASSWORD_RE.test(form.password) ? '8~24자, 영문과 숫자를 포함해야 합니다.' : '')
const confirmError  = computed(() => confirmPassword.value && form.password !== confirmPassword.value ? '비밀번호가 일치하지 않습니다.' : '')
const codeError     = computed(() => form.code && !/^\d{6}$/.test(form.code)           ? '6자리 숫자를 입력해주세요.' : '')

const canSendCode    = computed(() => EMAIL_RE.test(form.email) && !isEmailVerified.value && !loading.value)
const canVerifyCode  = computed(() => /^\d{6}$/.test(form.code) && !loading.value)
const isFormValid    = computed(() =>
  isEmailVerified.value &&
  NICKNAME_RE.test(form.nickname) &&
  PASSWORD_RE.test(form.password) &&
  form.password === confirmPassword.value
)

// ── 인증코드 발송 ────────────────────────────────────────────────────────
const sendCode = async () => {
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
      error.value = err.response?.data?.detail ?? '이메일 발송에 실패했습니다.'
    }
  } finally {
    loading.value = false
  }
}

// ── 인증코드 확인 ────────────────────────────────────────────────────────
const verifyCode = async () => {
  if (!canVerifyCode.value) return
  error.value   = ''
  loading.value = true
  try {
    await dbapi.post('/auth/verify-code', {
      email: form.email,
      code:  form.code,
    })
    isEmailVerified.value = true
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

// ── 최종 가입 ────────────────────────────────────────────────────────────
const handleRegister = async () => {
  if (!isFormValid.value || loading.value) return
  error.value   = ''
  loading.value = true
  try {
    await dbapi.post('/auth/register', {
      email:    form.email.trim().toLowerCase(),
      nickname: form.nickname.trim(),
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

        <SocialLoginButtons
          :on-needs-password="onSocialNeedsPassword"
          :on-requires-link-confirm="onSocialRequiresLinkConfirm"
          @done="onSocialDone"
        />

        <!-- 구분선 -->
        <div class="flex items-center gap-3 my-5">
          <div class="flex-1 h-px" :class="theme.isDark ? 'bg-[#2A2D3A]' : 'bg-gray-200'" />
          <span class="text-xs" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">또는 이메일로 가입</span>
          <div class="flex-1 h-px" :class="theme.isDark ? 'bg-[#2A2D3A]' : 'bg-gray-200'" />
        </div>

      <form @submit.prevent="handleRegister" class="space-y-4" novalidate>

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
              autocomplete="email"
              :disabled="isEmailVerified"
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
                ? 'bg-white/10 text-gray-300 hover:bg-white/20 disabled:hover:bg-white/10'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:hover:bg-gray-100'"
              @click="sendCode"
            >
              {{ isCodeSent ? '재발송' : '코드 발송' }}
            </button>
          </div>
          <p v-if="emailError" class="text-red-500 text-xs mt-1">{{ emailError }}</p>
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
              class="shrink-0 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50 bg-green-600 text-white hover:bg-green-700"
              @click="verifyCode"
            >
              인증하기
            </button>
          </div>
          <p v-if="codeError" class="text-red-500 text-xs mt-1">{{ codeError }}</p>
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
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            닉네임
          </label>
          <input
            v-model="form.nickname"
            type="text"
            placeholder="2~20자 (한글, 영문, 숫자, _)"
            autocomplete="username"
            required
            class="w-full rounded-xl px-4 py-2.5 text-sm border outline-none transition-colors"
            :class="[
              theme.isDark
                ? 'bg-[#0F1117] border-[#2A2D3A] text-white placeholder-gray-600 focus:border-indigo-500'
                : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-indigo-400',
              nicknameError ? 'border-red-500 focus:border-red-500' : ''
            ]"
          />
          <p v-if="nicknameError" class="text-red-500 text-xs mt-1">{{ nicknameError }}</p>
        </div>

        <!-- 비밀번호 -->
        <div>
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            비밀번호
          </label>
          <input
            v-model="form.password"
            type="password"
            placeholder="영문, 숫자 포함 8~24자"
            autocomplete="new-password"
            required
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

        <!-- 비밀번호 확인 -->
        <div>
          <label class="block text-sm font-medium mb-1.5" :class="theme.isDark ? 'text-gray-300' : 'text-gray-700'">
            비밀번호 확인
          </label>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="비밀번호 재입력"
            autocomplete="new-password"
            required
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

        <!-- 에러 -->
        <p v-if="error" role="alert" class="text-red-500 text-sm">{{ error }}</p>

        <!-- 제출 -->
        <button
          type="submit"
          :disabled="!isFormValid || loading"
          class="w-full py-2.5 rounded-xl font-semibold text-sm transition-colors mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
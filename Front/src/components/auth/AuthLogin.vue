<template>
  <div class="flex flex-col items-center gap-3.5 w-full max-w-[320px] px-7">

    <!-- 브랜드 마크 -->
    <div class="flex flex-col items-center gap-2">
      <h1 class="text-white font-black text-[28px] tracking-tight leading-none">Wallet Protector</h1>
      <p class="text-[11px] font-semibold tracking-[0.28em]"
         style="color: rgba(201,162,39,0.6)">SMART INVESTMENT</p>
    </div>

    <!-- 구분선 -->
    <div class="w-full h-px"
         style="background: linear-gradient(to right, transparent, rgba(201,162,39,0.28), transparent)"></div>

    <!-- 로그인 폼 -->
    <form @submit.prevent class="w-full space-y-1.5">

      <!-- 이메일 -->
      <div>
        <div class="relative">
          <LucideMail class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
                      style="color: rgba(255,255,255,0.25)" />
          <input v-model="email" type="text" placeholder="이메일"
            @input="emailTouched = true" @blur="emailTouched = true"
            class="w-full pl-11 pr-4 py-3.5 rounded-xl text-[15px] outline-none transition-all auth-input"
            :class="emailError ? 'err' : (email && !emailError ? 'ok' : '')" />
        </div>
        <div class="min-h-[14px] mt-0.5 px-1">
          <p v-if="emailError" class="text-[11px] flex items-center gap-1" style="color: rgba(248,113,113,0.8)">
            <LucideAlertCircle class="w-3 h-3 flex-shrink-0" />{{ emailError }}
          </p>
        </div>
      </div>

      <!-- 비밀번호 -->
      <div>
        <div class="relative">
          <LucideKeyRound class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
                          style="color: rgba(255,255,255,0.25)" />
          <input v-model="password" type="password" placeholder="비밀번호"
            @blur="passwordTouched = true"
            class="w-full pl-11 pr-4 py-3.5 rounded-xl text-[15px] outline-none transition-all auth-input"
            :class="passwordError ? 'err' : (password && !passwordError ? 'ok' : '')" />
        </div>
        <div class="min-h-[14px] mt-0.5 px-1">
          <p v-if="passwordError || apiError" class="text-[11px] flex items-center gap-1" style="color: rgba(248,113,113,0.8)">
            <LucideAlertCircle class="w-3 h-3 flex-shrink-0" />{{ passwordError || apiError }}
          </p>
        </div>
      </div>

    </form>

    <!-- 소셜 로그인 -->
    <div class="w-full flex flex-col items-center gap-2">
      <div class="flex items-center gap-2.5 w-full">
        <div class="flex-1 h-px" style="background: rgba(255,255,255,0.08)"></div>
        <span class="text-[11px] font-medium" style="color: rgba(255,255,255,0.28)">소셜 로그인</span>
        <div class="flex-1 h-px" style="background: rgba(255,255,255,0.08)"></div>
      </div>
      <SocialLoginButtons
        @done="emit('login-success')"
        :onNeedsPassword="handleNeedsPassword"
        :onRequiresLinkConfirm="handleRequiresLinkConfirm"
      />
    </div>

    <!-- 소셜 계정 연동 모달 -->
    <LinkConfirmModal
      v-if="showLinkModal"
      :linkHintToken="linkHintToken"
      :provider="linkProvider"
      @confirmed="onLinkConfirmed"
      @cancel="showLinkModal = false"
    />
    <SetPasswordModal
      v-if="showPwModal"
      :nickname="pwModalNickname"
      @done="onPwDone"
      @skip="onPwDone"
    />

    <!-- 하단 링크 -->
    <div class="flex items-center gap-4">
      <button @click="emit('go-signup')"
              class="text-[12px] font-medium transition-colors auth-link">
        회원가입
      </button>
      <span class="w-px h-3.5" style="background: rgba(255,255,255,0.15)"></span>
      <button @click="emit('go-find')"
              class="text-[12px] font-medium transition-colors auth-link">
        비밀번호 찾기
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { LucideAlertCircle, LucideMail, LucideKeyRound } from 'lucide-vue-next'
import authApi from '@/api/auth.js'
import { useAuthStore } from '@/stores/auth.js'
import SocialLoginButtons from './SocialLoginButtons.vue'
import LinkConfirmModal   from './LinkConfirmModal.vue'
import SetPasswordModal   from './SetPasswordModal.vue'

const emit = defineEmits(['go-signup', 'go-find', 'login-success'])
const authStore = useAuthStore()

const email           = ref('')
const password        = ref('')
const emailTouched    = ref(false)
const passwordTouched = ref(false)
const apiError        = ref('')

const emailError = computed(() => {
  if (!emailTouched.value) return null
  if (!email.value)                                       return '이메일을 입력해주세요'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))  return '올바른 이메일 형식을 입력해주세요'
  return null
})

const passwordError = computed(() => {
  if (!passwordTouched.value) return null
  if (!password.value)           return '비밀번호를 입력해주세요'
  if (password.value.length < 6) return '비밀번호는 6자 이상이어야 합니다'
  return null
})

const isFormValid = computed(() =>
  email.value && password.value && !emailError.value && !passwordError.value
)

function validate() {
  emailTouched.value    = true
  passwordTouched.value = true
  apiError.value        = ''
  return isFormValid.value
}

async function login() {
  if (!validate()) return false

  // 테스트 계정
  if (email.value === 'test1234@gmail.com' && password.value === 'test1234') {
    authStore.login('test-session-token', 'Admin', 'test-user-001')
    return true
  }

  try {
    const { data } = await authApi.login({ email: email.value, password: password.value })
    authStore.login(data.session_token, data.nickname, data.user_id ?? email.value)
    return true
  } catch (err) {
    const status = err.response?.status
    if (status === 401 || status === 400) {
      apiError.value = '이메일 또는 비밀번호가 올바르지 않습니다'
    } else if (status === 429) {
      apiError.value = '잠시 후 다시 시도해주세요'
    } else {
      apiError.value = err.response?.data?.detail ?? '로그인에 실패했습니다'
    }
    return false
  }
}

// 소셜 로그인 모달 상태
const showLinkModal   = ref(false)
const linkHintToken   = ref('')
const linkProvider    = ref('')
const showPwModal     = ref(false)
const pwModalNickname = ref('')

function handleRequiresLinkConfirm(token, provider) {
  linkHintToken.value = token
  linkProvider.value  = provider
  showLinkModal.value = true
}
function handleNeedsPassword(_token, nickname) {
  pwModalNickname.value = nickname
  showPwModal.value     = true
}
function onLinkConfirmed() {
  showLinkModal.value = false
  emit('login-success')
}
function onPwDone() {
  showPwModal.value = false
  emit('login-success')
}

defineExpose({ validate, login })
</script>

<style scoped>
.auth-input {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.09);
  color: rgba(255, 255, 255, 0.9);
}
.auth-input::placeholder {
  color: rgba(255, 255, 255, 0.22);
}
.auth-input:focus {
  border-color: rgba(201, 162, 39, 0.4);
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.07);
}
.auth-input.ok  { border-color: rgba(52, 211, 153, 0.38); }
.auth-input.err { border-color: rgba(248, 113, 113, 0.48); }
.auth-link {
  color: rgba(255, 255, 255, 0.32);
}
.auth-link:hover {
  color: rgba(201, 162, 39, 0.78);
}
</style>

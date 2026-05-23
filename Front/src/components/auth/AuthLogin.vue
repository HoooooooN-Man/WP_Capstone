<template>
  <div class="flex flex-col items-center gap-4 w-full max-w-[320px] px-6">

    <div class="text-center w-full">
      <h1 class="font-black text-white tracking-tighter uppercase italic leading-none"
          style="font-size: clamp(24px, 5vw, 38px); text-shadow: 0 2px 30px rgba(0,0,0,0.9), 0 0 50px rgba(100,75,15,0.25)"
      >WALLET PROTECTOR</h1>
      <div class="h-px w-16 bg-gradient-to-r from-transparent via-[#c9a227]/55 to-transparent mt-2.5 mx-auto"></div>
      <p class="text-[8px] text-[#9a7418] font-bold uppercase tracking-[0.35em] mt-1.5">Advanced Security Access</p>
    </div>

    <form @submit.prevent class="w-full space-y-1.5">
      <div>
        <input v-model="email" type="text" placeholder="EMAIL ADDRESS"
          @input="emailTouched = true" @blur="emailTouched = true"
          class="w-full px-4 py-3 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.18em] shadow-inner transition-all"
          :class="emailError ? 'border-red-500/60' : (email && !emailError ? 'border-green-500/40' : 'border-white/10')" />
        <div class="min-h-[14px] mt-0.5 px-1">
          <p v-if="emailError" class="text-[9px] text-red-400/80 flex items-center gap-1">
            <LucideAlertCircle class="w-2.5 h-2.5 flex-shrink-0"/>{{ emailError }}
          </p>
        </div>
      </div>
      <div>
        <input v-model="password" type="password" placeholder="PASSWORD"
          @blur="passwordTouched = true"
          class="w-full px-4 py-3 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.18em] shadow-inner transition-all"
          :class="passwordError ? 'border-red-500/60' : (password && !passwordError ? 'border-green-500/40' : 'border-white/10')" />
        <div class="min-h-[14px] mt-0.5 px-1">
          <p v-if="passwordError" class="text-[9px] text-red-400/80 flex items-center gap-1">
            <LucideAlertCircle class="w-2.5 h-2.5 flex-shrink-0"/>{{ passwordError }}
          </p>
          <p v-else-if="apiError" class="text-[9px] text-red-400/80 flex items-center gap-1">
            <LucideAlertCircle class="w-2.5 h-2.5 flex-shrink-0"/>{{ apiError }}
          </p>
        </div>
      </div>
    </form>

    <!-- 소셜 로그인 -->
    <div class="flex flex-col items-center w-full">
      <div class="flex items-center gap-3 mb-2.5 w-full">
        <div class="flex-1 h-px bg-gradient-to-r from-transparent to-white/10"></div>
        <span class="text-[8px] text-[#7a5c20]/70 uppercase tracking-[0.3em] font-semibold">or</span>
        <div class="flex-1 h-px bg-gradient-to-l from-transparent to-white/10"></div>
      </div>
      <SocialLoginButtons @done="emit('login-success')" />
    </div>

    <!-- 하단 링크 -->
    <div class="flex items-center gap-3">
      <button @click="emit('go-signup')"
              class="text-[9px] text-[#7a5c20]/70 hover:text-[#c9a227]/80 transition-colors uppercase tracking-widest font-semibold">
        회원가입
      </button>
      <span class="w-px h-3 bg-white/15 flex-shrink-0"></span>
      <button @click="emit('go-find')"
              class="text-[9px] text-[#7a5c20]/70 hover:text-[#c9a227]/80 transition-colors uppercase tracking-widest font-semibold">
        아이디 / 비밀번호 찾기
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { LucideAlertCircle } from 'lucide-vue-next'
import authApi from '@/api/auth.js'
import { useAuthStore } from '@/stores/auth.js'
import SocialLoginButtons from './SocialLoginButtons.vue'

const emit = defineEmits(['go-signup', 'go-find', 'login-success'])

const authStore = useAuthStore()

const email           = ref('')
const password        = ref('')
const emailTouched    = ref(false)
const passwordTouched = ref(false)
const apiError        = ref('')

const emailError = computed(() => {
  if (!emailTouched.value) return null
  if (!email.value)                                        return '이메일을 입력해주세요'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))   return '올바른 이메일 형식을 입력해주세요'
  return null
})

const passwordError = computed(() => {
  if (!passwordTouched.value) return null
  if (!password.value)        return '비밀번호를 입력해주세요'
  if (password.value.length < 6) return '비밀번호는 6자 이상이어야 합니다'
  return null
})

const isFormValid = computed(() =>
  email.value && password.value &&
  !emailError.value && !passwordError.value
)

function validate() {
  emailTouched.value    = true
  passwordTouched.value = true
  apiError.value        = ''
  return isFormValid.value
}

async function login() {
  if (!validate()) return false
  try {
    const { data } = await authApi.login({ email: email.value, password: password.value })
    authStore.login(data.session_token, data.nickname, data.user_id)
    return true
  } catch (err) {
    const status = err.response?.status
    if (status === 401 || status === 400) {
      apiError.value = '이메일 또는 비밀번호가 올바르지 않습니다'
    } else if (status === 429) {
      apiError.value = '요청이 너무 많습니다. 잠시 후 다시 시도해주세요'
    } else {
      apiError.value = err.response?.data?.detail ?? '로그인에 실패했습니다'
    }
    return false
  }
}

defineExpose({ validate, login })
</script>

<style scoped>
input:focus {
  border-color: rgba(201, 162, 39, 0.4);
  box-shadow: inset 0 0 0 1px rgba(201, 162, 39, 0.08), 0 0 12px rgba(150, 110, 20, 0.12);
}
</style>

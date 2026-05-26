<template>
  <div class="flex flex-col w-full max-w-[320px] px-6 gap-3">

    <!-- 헤더 -->
    <div class="flex items-center gap-3">
      <button @click="emit('go-login')"
              class="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 transition-all flex-shrink-0">
        <LucideChevronLeft class="w-3.5 h-3.5 text-white/60" />
      </button>
      <div>
        <p class="text-[8px] text-[#9a7418] font-bold uppercase tracking-[0.3em]">New Account</p>
        <h2 class="text-base font-black text-white tracking-tight uppercase leading-none">회원가입</h2>
      </div>
    </div>

    <!-- 입력 -->
    <div class="space-y-2">
      <input v-model="nickname" type="text" placeholder="닉네임"
        :class="['w-full px-4 py-2.5 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all',
          nicknameError ? 'border-red-500/60' : 'border-white/10']" />
      <p v-if="nicknameError" class="text-[9px] text-red-400/80 px-1 -mt-1">{{ nicknameError }}</p>
      <input v-model="email" type="text" placeholder="이메일"
        :class="['w-full px-4 py-2.5 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all',
          emailError ? 'border-red-500/60' : 'border-white/10']" />
      <p v-if="emailError" class="text-[9px] text-red-400/80 px-1 -mt-1">{{ emailError }}</p>
      <input v-model="pw" type="password" placeholder="비밀번호 (영문+숫자+특수문자 8~24자)"
        :class="['w-full px-4 py-2.5 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all',
          pwError ? 'border-red-500/60' : 'border-white/10']" />
      <p v-if="pwError" class="text-[9px] text-red-400/80 px-1 -mt-1">{{ pwError }}</p>
      <div>
        <input v-model="pwConfirm" type="password" placeholder="비밀번호 확인"
          class="w-full px-4 py-2.5 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all"
          :class="pwConfirm && pw !== pwConfirm ? 'border-red-500/60' : 'border-white/10'" />
        <p v-if="pwConfirm && pw !== pwConfirm"
           class="text-[9px] text-red-400/80 flex items-center gap-1 px-1 mt-0.5">
          <LucideAlertCircle class="w-2.5 h-2.5 flex-shrink-0"/>비밀번호가 일치하지 않습니다
        </p>
      </div>
    </div>

    <p v-if="apiError" class="text-[9px] text-red-400/80 text-center">{{ apiError }}</p>
    <p v-if="successMsg" class="text-[9px] text-green-400/80 text-center">{{ successMsg }}</p>

    <button
      :disabled="loading"
      @click="handleRegister"
      class="w-full py-2.5 bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 rounded-xl text-[11px] font-black text-[#1a0e04] tracking-[0.2em] uppercase hover:brightness-110 active:scale-[0.98] transition-all shadow-[0_4px_12px_rgba(0,0,0,0.4)] disabled:opacity-60 disabled:cursor-not-allowed"
    >
      {{ loading ? '처리 중...' : '가입하기' }}
    </button>

    <p class="text-center text-[9px] text-[#7a5c20]/60">
      이미 계정이 있으신가요?
      <button @click="emit('go-login')" class="text-[#c9a227]/70 hover:text-[#c9a227] ml-1 font-semibold transition-colors">로그인</button>
    </p>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { LucideChevronLeft, LucideAlertCircle } from 'lucide-vue-next'
import authApi from '@/api/auth.js'

const emit = defineEmits(['go-login'])

const nickname  = ref('')
const email     = ref('')
const pw        = ref('')
const pwConfirm = ref('')
const loading   = ref(false)
const apiError  = ref('')
const successMsg = ref('')

const nicknameError = computed(() => {
  if (!nickname.value) return null
  if (nickname.value.length < 2) return '닉네임은 2자 이상이어야 합니다'
  return null
})

const emailError = computed(() => {
  if (!email.value) return null
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) return '올바른 이메일 형식을 입력해주세요'
  return null
})

// 백엔드 요구사항: 영문+숫자+특수문자(@$!%*#?&) 포함 8~24자
const PW_RE = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,24}$/
const pwError = computed(() => {
  if (!pw.value) return null
  if (!PW_RE.test(pw.value)) return '영문·숫자·특수문자(@$!%*#?&) 포함 8~24자'
  return null
})

async function handleRegister() {
  apiError.value  = ''
  successMsg.value = ''

  if (!nickname.value || !email.value || !pw.value || !pwConfirm.value) {
    apiError.value = '모든 항목을 입력해주세요'
    return
  }
  if (nicknameError.value || emailError.value || pwError.value) return
  if (pw.value !== pwConfirm.value) return

  loading.value = true
  try {
    await authApi.register({ nickname: nickname.value, email: email.value, password: pw.value })
    successMsg.value = '가입 완료! 로그인해주세요'
    setTimeout(() => emit('go-login'), 1500)
  } catch (err) {
    const status = err.response?.status
    if (status === 409) apiError.value = '이미 사용 중인 이메일 또는 닉네임입니다'
    else apiError.value = err.response?.data?.detail ?? '회원가입에 실패했습니다'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
input:focus {
  border-color: rgba(201, 162, 39, 0.4);
  box-shadow: inset 0 0 0 1px rgba(201, 162, 39, 0.08), 0 0 12px rgba(150, 110, 20, 0.12);
}
</style>

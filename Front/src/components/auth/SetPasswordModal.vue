<!-- needs_password: true 응답 시 — 소셜 전용 계정에 비밀번호 설정 유도 -->
<template>
  <div
    class="fixed inset-0 z-[200] flex items-center justify-center px-4"
    style="background: rgba(0,0,0,0.72); backdrop-filter: blur(4px);"
    @click.self="emit('skip')"
  >
    <div class="w-full max-w-[300px] bg-gradient-to-br from-[#1e1408] via-[#161008] to-[#1a1205] border border-[#c9a227]/25 rounded-2xl p-6 shadow-[0_30px_80px_rgba(0,0,0,0.8)]">

      <!-- 아이콘 + 제목 -->
      <div class="text-center mb-5">
        <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-[#c9a227]/10 border border-[#c9a227]/25 flex items-center justify-center">
          <svg class="w-6 h-6 text-[#c9a227]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
          </svg>
        </div>
        <h2 class="text-sm font-black text-white tracking-tight uppercase">비밀번호 설정</h2>
        <p class="text-[12px] text-white/45 mt-1.5 leading-relaxed">
          <span class="text-[#c9a227]/80 font-bold">{{ nickname }}</span>님,<br>비밀번호를 설정하면 이메일로도 로그인할 수 있어요.
        </p>
      </div>

      <div class="space-y-2">
        <div>
          <input
            v-model="password"
            type="password"
            placeholder="영문, 숫자 포함 8~24자"
            autocomplete="new-password"
            class="w-full px-4 py-2.5 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all"
            :class="passwordError ? 'border-red-500/60' : 'border-white/10'"
          />
          <p v-if="passwordError" class="text-[11px] text-red-400/80 px-1 mt-0.5">{{ passwordError }}</p>
        </div>
        <div>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="비밀번호 재입력"
            autocomplete="new-password"
            class="w-full px-4 py-2.5 bg-black/50 border rounded-xl text-[11px] text-white/90 placeholder:text-[#5a4020]/80 outline-none tracking-[0.15em] shadow-inner transition-all"
            :class="confirmError ? 'border-red-500/60' : 'border-white/10'"
          />
          <p v-if="confirmError" class="text-[11px] text-red-400/80 px-1 mt-0.5">{{ confirmError }}</p>
        </div>

        <p v-if="apiError" role="alert" class="text-[11px] text-red-400/80 text-center">{{ apiError }}</p>

        <button
          type="button"
          :disabled="!isValid || loading"
          class="w-full py-2.5 rounded-xl text-[11px] font-black transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 text-[#1a0e04] hover:brightness-110 active:scale-[0.98] shadow-[0_4px_12px_rgba(0,0,0,0.4)]"
          @click="handleSubmit"
        >
          {{ loading ? '설정 중...' : '비밀번호 설정하기' }}
        </button>

        <button
          type="button"
          class="w-full py-1.5 text-[12px] text-[#7a5c20]/55 hover:text-[#c9a227]/70 transition-colors font-semibold text-center"
          @click="emit('skip')"
        >
          나중에 설정하기
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import dbapi from '@/api/dbapi'

const props = defineProps({
  nickname: { type: String, default: '' },
})
const emit = defineEmits(['done', 'skip'])

const password        = ref('')
const confirmPassword = ref('')
const loading         = ref(false)
const apiError        = ref('')

const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,24}$/

const passwordError = computed(() =>
  password.value && !PASSWORD_RE.test(password.value)
    ? '8~24자, 영문과 숫자를 포함해야 합니다.' : ''
)
const confirmError = computed(() =>
  confirmPassword.value && password.value !== confirmPassword.value
    ? '비밀번호가 일치하지 않습니다.' : ''
)
const isValid = computed(() =>
  PASSWORD_RE.test(password.value) && password.value === confirmPassword.value
)

async function handleSubmit() {
  if (!isValid.value || loading.value) return
  apiError.value = ''
  loading.value  = true
  try {
    await dbapi.post('/auth/set-password', { new_password: password.value })
    emit('done')
  } catch (err) {
    apiError.value = err.response?.data?.detail ?? '비밀번호 설정에 실패했습니다.'
    password.value        = ''
    confirmPassword.value = ''
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

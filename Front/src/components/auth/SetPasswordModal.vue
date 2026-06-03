<!-- needs_password: true 응답 시 — 소셜 전용 계정에 비밀번호 설정 유도 -->
<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme.js'
import dbapi from '@/api/dbapi'

const props = defineProps({
  nickname: { type: String, default: '' },
})
const emit = defineEmits(['close', 'done'])

const router  = useRouter()
const theme   = useThemeStore()

const password        = ref('')
const confirmPassword = ref('')
const loading         = ref(false)
const error           = ref('')
const skipped         = ref(false)

const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,24}$/

const passwordError = computed(() => password.value        && !PASSWORD_RE.test(password.value)         ? '8~24자, 영문과 숫자를 포함해야 합니다.' : '')
const confirmError  = computed(() => confirmPassword.value && password.value !== confirmPassword.value  ? '비밀번호가 일치하지 않습니다.' : '')
const isValid       = computed(() => PASSWORD_RE.test(password.value) && password.value === confirmPassword.value)

const handleSkip = () => {
  skipped.value = true
  router.push('/')
  emit('close')
}

const handleSubmit = async () => {
  if (!isValid.value || loading.value) return
  error.value   = ''
  loading.value = true
  try {
    // 세션이 이미 있으므로 reset-password 엔드포인트 사용
    // current_password 없이 소셜 전용 계정 비밀번호 설정은
    // 별도 /auth/set-password 엔드포인트를 백엔드에 추가하거나
    // reset-password-via-email 흐름을 재활용 가능
    await dbapi.post('/auth/set-password', {
      new_password: password.value,
    })
    emit('done')
    router.push('/')
  } catch (err) {
    error.value = err.response?.data?.detail ?? '비밀번호 설정에 실패했습니다.'
    password.value        = ''
    confirmPassword.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <!-- 오버레이 -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center px-4"
    style="background: rgba(0,0,0,0.55)"
    @click.self="handleSkip"
  >
    <div
      class="w-full max-w-sm rounded-2xl p-7 shadow-xl"
      :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white'"
    >
      <div class="text-center mb-6">
        <p class="text-2xl mb-1">🔐</p>
        <h2 class="text-lg font-bold">비밀번호 설정</h2>
        <p class="text-sm mt-1" :class="theme.isDark ? 'text-gray-400' : 'text-gray-500'">
          <span class="font-medium">{{ nickname }}</span>님, 비밀번호를 설정하면<br>이메일로도 로그인할 수 있어요.
        </p>
      </div>

      <div class="space-y-3">
        <div>
          <input
            v-model="password"
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

        <p v-if="error" role="alert" class="text-red-500 text-xs">{{ error }}</p>

        <button
          type="button"
          :disabled="!isValid || loading"
          class="w-full py-2.5 rounded-xl font-semibold text-sm transition-colors disabled:opacity-50 bg-indigo-600 text-white hover:bg-indigo-700"
          @click="handleSubmit"
        >
          {{ loading ? '설정 중...' : '비밀번호 설정하기' }}
        </button>

        <button
          type="button"
          class="w-full py-2 text-sm transition-colors"
          :class="theme.isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'"
          @click="handleSkip"
        >
          나중에 설정하기
        </button>
      </div>
    </div>
  </div>
</template>
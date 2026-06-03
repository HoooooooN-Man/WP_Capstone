<!-- requires_link_confirmation: true — 기존 이메일 계정과 소셜 연동 동의 -->
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme.js'
import { useAuthStore } from '@/stores/auth.js'
import dbapi from '@/api/dbapi'

const props = defineProps({
  linkHintToken: { type: String, required: true },
  provider:      { type: String, required: true },
})
const emit = defineEmits(['close'])

const router = useRouter()
const theme  = useThemeStore()
const auth   = useAuthStore()

const loading = ref(false)
const error   = ref('')

const PROVIDER_LABELS = { google: 'Google', kakao: '카카오', naver: '네이버' }

const handleConfirm = async () => {
  if (loading.value) return
  error.value   = ''
  loading.value = true
  try {
    const { data } = await dbapi.post(`/auth/link/${props.provider}`, {
      link_hint_token: props.linkHintToken,
    })
    auth.login(data.session_token, data.nickname, data.user_id)
    emit('close')
    router.push('/')
  } catch (err) {
    error.value = err.response?.data?.detail ?? '계정 연동에 실패했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center px-4"
    style="background: rgba(0,0,0,0.55)"
    @click.self="emit('close')"
  >
    <div
      class="w-full max-w-sm rounded-2xl p-7 shadow-xl"
      :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white'"
    >
      <div class="text-center mb-6">
        <p class="text-2xl mb-1">🔗</p>
        <h2 class="text-lg font-bold">기존 계정과 연동</h2>
        <p class="text-sm mt-2 leading-relaxed" :class="theme.isDark ? 'text-gray-400' : 'text-gray-500'">
          이미 해당 이메일로 가입된 계정이 있습니다.<br>
          <span class="font-medium" :class="theme.isDark ? 'text-gray-200' : 'text-gray-800'">
            {{ PROVIDER_LABELS[provider] }}
          </span> 계정을 기존 계정에 연동하시겠습니까?
        </p>
      </div>

      <p v-if="error" role="alert" class="text-red-500 text-xs text-center mb-3">{{ error }}</p>

      <div class="flex gap-2">
        <button
          type="button"
          class="flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors border"
          :class="theme.isDark
            ? 'border-[#2A2D3A] text-gray-400 hover:bg-white/5'
            : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
          @click="emit('close')"
        >
          취소
        </button>
        <button
          type="button"
          :disabled="loading"
          class="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 bg-indigo-600 text-white hover:bg-indigo-700"
          @click="handleConfirm"
        >
          {{ loading ? '연동 중...' : '연동하기' }}
        </button>
      </div>
    </div>
  </div>
</template>
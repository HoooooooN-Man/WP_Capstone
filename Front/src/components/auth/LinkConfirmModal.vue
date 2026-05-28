<!-- requires_link_confirmation: true — 기존 이메일 계정과 소셜 연동 동의 -->
<template>
  <div
    class="fixed inset-0 z-[200] flex items-center justify-center px-4"
    style="background: rgba(0,0,0,0.72); backdrop-filter: blur(4px);"
    @click.self="emit('cancel')"
  >
    <div class="w-full max-w-[300px] bg-gradient-to-br from-[#1e1408] via-[#161008] to-[#1a1205] border border-[#c9a227]/25 rounded-2xl p-6 shadow-[0_30px_80px_rgba(0,0,0,0.8)]">

      <!-- 아이콘 + 제목 -->
      <div class="text-center mb-5">
        <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-[#c9a227]/10 border border-[#c9a227]/25 flex items-center justify-center">
          <svg class="w-6 h-6 text-[#c9a227]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
          </svg>
        </div>
        <h2 class="text-sm font-black text-white tracking-tight uppercase">계정 연동</h2>
        <p class="text-[12px] text-white/45 mt-1.5 leading-relaxed">
          이미 해당 이메일로 가입된 계정이 있습니다.<br>
          <span class="text-[#c9a227]/80 font-bold">{{ PROVIDER_LABELS[provider] }}</span> 계정을 기존 계정에 연동하시겠습니까?
        </p>
      </div>

      <p v-if="error" role="alert" class="text-[11px] text-red-400/80 text-center mb-3">{{ error }}</p>

      <div class="flex gap-2">
        <button
          type="button"
          class="flex-1 py-2 rounded-xl text-[11px] font-bold transition-all border border-white/10 text-white/40 hover:bg-white/5 hover:text-white/60"
          @click="emit('cancel')"
        >
          취소
        </button>
        <button
          type="button"
          :disabled="loading"
          class="flex-1 py-2 rounded-xl text-[11px] font-black transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-[#c9a227]/80 to-[#9a7218]/80 text-[#1a0e04] hover:brightness-110 active:scale-[0.98] shadow-[0_4px_12px_rgba(0,0,0,0.4)]"
          @click="handleConfirm"
        >
          {{ loading ? '연동 중...' : '연동하기' }}
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import dbapi from '@/api/dbapi'

const props = defineProps({
  linkHintToken: { type: String, required: true },
  provider:      { type: String, required: true },
})
const emit = defineEmits(['confirmed', 'cancel'])

const auth    = useAuthStore()
const loading = ref(false)
const error   = ref('')

const PROVIDER_LABELS = { google: 'Google', kakao: '카카오', naver: '네이버' }

async function handleConfirm() {
  if (loading.value) return
  error.value   = ''
  loading.value = true
  try {
    const { data } = await dbapi.post(`/auth/link/${props.provider}`, {
      link_hint_token: props.linkHintToken,
    })
    auth.login(data.session_token, data.nickname, data.user_id)
    emit('confirmed')
  } catch (err) {
    error.value = err.response?.data?.detail ?? '계정 연동에 실패했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

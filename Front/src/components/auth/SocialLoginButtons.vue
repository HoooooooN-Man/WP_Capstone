<script setup>
import { ref } from 'vue'
import { useThemeStore } from '@/stores/theme.js'
import { useAuthStore } from '@/stores/auth.js'
import dbapi from '@/api/dbapi'

const props = defineProps({
  // 부모에서 후처리 흐름 제어
  onNeedsPassword:       Function, // (token, nickname) => void
  onRequiresLinkConfirm: Function, // (linkHintToken, provider) => void
})

const theme  = useThemeStore()
const auth   = useAuthStore()

const loadingProvider = ref(null) // 어떤 버튼이 로딩 중인지
const error           = ref('')

const PROVIDERS = [
  {
    id:   'google',
    label: 'Google',
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>`,
  },
  {
    id:    'kakao',
    label: '카카오',
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 3C6.477 3 2 6.477 2 10.5c0 2.584 1.574 4.857 3.969 6.22l-.994 3.695a.375.375 0 0 0 .553.415L9.86 18.54A11.578 11.578 0 0 0 12 18c5.523 0 10-3.477 10-7.5S17.523 3 12 3z" fill="#3C1E1E"/>
    </svg>`,
    kakaoColor: true,
  },
  {
    id:    'naver',
    label: '네이버',
    icon: `<svg viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
      <path d="M13.6 12.4 10.1 7H7v10h3.4v-5.4L14 17H17V7h-3.4z" fill="white"/>
    </svg>`,
    naverColor: true,
  },
]

// 소셜 SDK로 Access Token을 획득한 뒤 백엔드로 전달하는 공통 함수
// 현재는 팝업/SDK 연동을 직접 구현하지 않으므로,
// 각 플랫폼 SDK 초기화 후 이 함수에서 토큰을 받아 처리
async function handleSocialLogin(provider) {
  if (loadingProvider.value) return
  error.value = ''
  loadingProvider.value = provider

  try {
    let accessToken = ''
    if (provider === 'google')      accessToken = await getGoogleToken()
    else if (provider === 'kakao')  accessToken = await getKakaoToken()
    else if (provider === 'naver')  accessToken = await getNaverToken()

    const { data } = await dbapi.post(`/auth/login/${provider}`, {
      access_token: accessToken,
    })

    if (data.requires_link_confirmation) {
      props.onRequiresLinkConfirm?.(data.link_hint_token, provider)
      return
    }

    auth.login(data.session_token, data.nickname, data.user_id)

    if (data.needs_password) {
      props.onNeedsPassword?.(data.session_token, data.nickname)
    } else {
      emit('done')  // ← 추가
    }

  } catch (err) {
    const status = err.response?.status
    if (status === 429) error.value = '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.'
    else error.value = err.response?.data?.detail ?? `${provider} 로그인에 실패했습니다.`
  } finally {
    loadingProvider.value = null
  }
}

// ── 플랫폼별 토큰 획득 스텁 ──────────────────────────────────────────────
// 실제 SDK 연동 시 아래 함수들을 구현하세요.

function getGoogleToken() {
  return new Promise((resolve, reject) => {
    if (!window.google?.accounts?.oauth2) {
      reject(new Error('Google SDK가 로드되지 않았습니다.'))
      return
    }
    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
      scope: 'email profile',
      callback: (res) => {
        if (res.error) reject(new Error(res.error))
        else resolve(res.access_token)
      },
    })
    client.requestAccessToken()
  })
}

function getKakaoToken() {
  return new Promise((resolve, reject) => {
    const redirectUri = 'http://localhost:8000/auth/kakao/callback'
    const kakaoAuthUrl =
      `https://kauth.kakao.com/oauth/authorize?response_type=code` +
      `&client_id=${import.meta.env.VITE_KAKAO_REST_KEY}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}`

    const popup = window.open(kakaoAuthUrl, 'kakao_login', 'width=500,height=600')

    const timer = setInterval(() => {
      if (popup?.closed) {
        clearInterval(timer)
        reject(new Error('카카오 로그인 창이 닫혔습니다.'))
      }
    }, 500)

    window.addEventListener('message', function handler(e) {
      if (e.origin !== 'http://localhost:8000') return
      clearInterval(timer)
      window.removeEventListener('message', handler)
      popup?.close()

      if (e.data?.error) reject(new Error(e.data.error))
      else if (e.data?.access_token) resolve(e.data.access_token)
      else reject(new Error('카카오 토큰 수신 실패'))
    })
  })
}

function getNaverToken() {
  return new Promise((resolve, reject) => {
    const state = Math.random().toString(36).substring(2)
    const redirectUri = 'http://localhost:8000/auth/naver/callback'
    const naverAuthUrl =
      `https://nid.naver.com/oauth2.0/authorize?response_type=code` +
      `&client_id=${import.meta.env.VITE_NAVER_CLIENT_ID}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
      `&state=${state}`

    const popup = window.open(naverAuthUrl, 'naver_login', 'width=500,height=600')

    const timer = setInterval(() => {
      if (popup?.closed) {
        clearInterval(timer)
        reject(new Error('네이버 로그인 창이 닫혔습니다.'))
      }
    }, 500)

    window.addEventListener('message', function handler(e) {
      if (e.origin !== 'http://localhost:8000') return
      clearInterval(timer)
      window.removeEventListener('message', handler)
      popup?.close()

      if (e.data?.error) reject(new Error(e.data.error))
      else if (e.data?.access_token) resolve(e.data.access_token)
      else reject(new Error('네이버 토큰 수신 실패'))
    })
  })
}

const emit = defineEmits(['done'])
</script>

<template>
  <div class="space-y-3">
    <button
      v-for="p in PROVIDERS"
      :key="p.id"
      type="button"
      :disabled="!!loadingProvider"
      class="w-full flex items-center justify-center gap-3 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed border"
      :class="[
        p.kakaoColor
          ? 'bg-[#FEE500] border-[#FEE500] text-[#3C1E1E] hover:bg-[#F0D800]'
          : p.naverColor
            ? 'bg-[#03C75A] border-[#03C75A] text-white hover:bg-[#02B350]'
            : theme.isDark
              ? 'bg-white/5 border-[#2A2D3A] text-gray-300 hover:bg-white/10'
              : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
      ]"
      @click="handleSocialLogin(p.id)"
    >
      <!-- 로딩 스피너 or 아이콘 -->
      <span v-if="loadingProvider === p.id" class="w-[18px] h-[18px] flex items-center justify-center">
        <svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-dasharray="60" stroke-dashoffset="20" stroke-linecap="round"/>
        </svg>
      </span>
      <span v-else class="w-[18px] h-[18px] flex items-center justify-center" v-html="p.icon" />
      {{ p.label }}로 계속하기
    </button>

    <p v-if="error" role="alert" class="text-red-500 text-xs text-center">{{ error }}</p>
  </div>
</template>
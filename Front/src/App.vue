<script setup>
import { useAuthStore }  from '@/stores/auth.js'
import { useThemeStore } from '@/stores/theme.js'
import { useRouter }     from 'vue-router'

const auth   = useAuthStore()
const theme  = useThemeStore()
const router = useRouter()

const NAV_ITEMS = [
  { to: '/',          label: '홈' },
  { to: '/stocks',    label: '종목 추천' },
  { to: '/screener',  label: '스크리너' },
  { to: '/portfolio', label: '포트폴리오' },
  { to: '/compare',   label: '비교' },
]

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div
    id="app"
    class="min-h-screen flex flex-col transition-colors duration-200"
    :class="theme.isDark ? 'bg-[#0F1117] text-[#E4E6EF]' : 'bg-white text-gray-900'"
  >

    <!-- ── 상단 네비게이션 ───────────────────────────────────── -->
    <header
      class="sticky top-0 z-50 border-b transition-colors duration-200"
      :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
    >
      <div class="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">

        <!-- 로고 -->
        <RouterLink to="/" class="font-bold text-base shrink-0" :class="theme.isDark ? 'text-white' : 'text-gray-900'">
          WP_Capstone
        </RouterLink>

        <!-- 메뉴 -->
        <nav class="flex items-center gap-1 flex-1">
          <RouterLink
            v-for="item in NAV_ITEMS"
            :key="item.to"
            :to="item.to"
            class="px-3 py-1.5 rounded-md text-sm transition-colors"
            :class="theme.isDark
              ? 'text-gray-400 hover:text-gray-100 hover:bg-white/10 [&.router-link-active]:text-white [&.router-link-active]:bg-white/10 [&.router-link-active]:font-medium'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 [&.router-link-active]:text-gray-900 [&.router-link-active]:bg-gray-100 [&.router-link-active]:font-medium'"
            active-class="router-link-active"
            exact-active-class=""
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <!-- 우측: 다크 토글 + 로그인 -->
        <div class="flex items-center gap-2 shrink-0">

          <!-- 다크 모드 토글 -->
          <button
            class="w-8 h-8 flex items-center justify-center rounded-lg text-base transition-colors"
            :class="theme.isDark ? 'text-yellow-400 hover:bg-white/10' : 'text-gray-500 hover:bg-gray-100'"
            :title="theme.isDark ? '라이트 모드' : '다크 모드'"
            @click="theme.toggleDark()"
          >
            {{ theme.isDark ? '☀️' : '🌙' }}
          </button>

          <template v-if="auth.isLoggedIn">
            <RouterLink
              to="/my"
              class="text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-300 hover:text-white' : 'text-gray-700 hover:text-gray-900'"
            >
              {{ auth.nickname }}
            </RouterLink>
            <button
              class="text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'"
              @click="handleLogout"
            >
              로그아웃
            </button>
          </template>
          <template v-else>
            <RouterLink
              to="/login"
              class="text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'"
            >
              로그인
            </RouterLink>
            <RouterLink
              to="/register"
              class="text-sm px-3 py-1.5 rounded-md transition-colors"
              :class="theme.isDark ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-gray-900 text-white hover:bg-gray-700'"
            >
              회원가입
            </RouterLink>
          </template>
        </div>
      </div>
    </header>

    <!-- ── 페이지 콘텐츠 ─────────────────────────────────────── -->
    <main class="flex-1">
      <RouterView />
    </main>

  </div>
</template>

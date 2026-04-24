<script setup>
import { useAuthStore } from '@/stores/auth.js'
import { useRouter } from 'vue-router'

const auth   = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div id="app" class="min-h-screen bg-white text-gray-900 flex flex-col">

    <!-- ── 상단 네비게이션 ───────────────────────────────────── -->
    <header class="sticky top-0 z-50 bg-white border-b border-gray-100">
      <div class="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
        <!-- 로고 -->
        <RouterLink to="/" class="font-bold text-base text-gray-900 shrink-0">
          WP_Capstone
        </RouterLink>

        <!-- 메뉴 -->
        <nav class="flex items-center gap-1 flex-1">
          <RouterLink
            v-for="{ to, label } in [
              { to: '/',          label: '홈' },
              { to: '/stocks',    label: '종목 추천' },
              { to: '/screener',  label: '스크리너' },
              { to: '/portfolio', label: '포트폴리오' },
              { to: '/compare',   label: '비교' },
            ]"
            :key="to"
            :to="to"
            class="px-3 py-1.5 rounded-md text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors"
            active-class="text-gray-900 bg-gray-100 font-medium"
            exact-active-class=""
          >
            {{ label }}
          </RouterLink>
        </nav>

        <!-- 로그인/닉네임 -->
        <div class="flex items-center gap-2 shrink-0">
          <template v-if="auth.isLoggedIn">
            <RouterLink to="/my" class="text-sm text-gray-700 hover:text-gray-900">
              {{ auth.nickname }}
            </RouterLink>
            <button
              class="text-sm text-gray-400 hover:text-gray-600 transition-colors"
              @click="handleLogout"
            >
              로그아웃
            </button>
          </template>
          <template v-else>
            <RouterLink to="/login"    class="text-sm text-gray-600 hover:text-gray-900">로그인</RouterLink>
            <RouterLink to="/register" class="text-sm px-3 py-1.5 bg-gray-900 text-white rounded-md hover:bg-gray-700 transition-colors">
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

<script setup>
import { ref } from 'vue'
import { useAuthStore }     from '@/stores/auth.js'
import { useThemeStore }    from '@/stores/theme.js'
import { useRouter }        from 'vue-router'
import { useEventListener } from '@vueuse/core'
import GlobalSearch from '@/components/common/GlobalSearch.vue'

const auth   = useAuthStore()
const theme  = useThemeStore()
const router = useRouter()

// ── 글로벌 검색 단축키 Cmd+K / Ctrl+K ────────────────────────────────────────
const searchOpen = ref(false)

useEventListener(document, 'keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    searchOpen.value = !searchOpen.value
  }
})

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

          <!-- 검색 버튼 -->
          <button
            class="flex items-center gap-1.5 text-xs border rounded-lg px-2.5 py-1.5 transition-colors"
            :class="theme.isDark
              ? 'border-[#2A2D3A] text-gray-500 hover:bg-white/10'
              : 'border-gray-200 text-gray-400 hover:bg-gray-50'"
            @click="searchOpen = true"
          >
            <span>🔍</span>
            <span class="hidden sm:inline">검색</span>
            <kbd
              class="hidden sm:inline border rounded px-1 py-0.5 text-[10px]"
              :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-200'"
            >⌘K</kbd>
          </button>

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

  <!-- ── 글로벌 검색 모달 ─────────────────────────────────────── -->
  <Transition name="search-fade">
    <GlobalSearch v-if="searchOpen" @close="searchOpen = false" />
  </Transition>
</template>

<style scoped>
.search-fade-enter-active, .search-fade-leave-active { transition: opacity 0.15s; }
.search-fade-enter-from, .search-fade-leave-to { opacity: 0; }
</style>

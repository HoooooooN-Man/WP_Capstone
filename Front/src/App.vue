<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore }          from '@/stores/auth.js'
import { useThemeStore }         from '@/stores/theme.js'
import { useNotificationStore }  from '@/stores/notifications.js'
import { useRouter }             from 'vue-router'
import { useEventListener }      from '@vueuse/core'
import GlobalSearch from '@/components/common/GlobalSearch.vue'

const auth   = useAuthStore()
const theme  = useThemeStore()
const notif  = useNotificationStore()
const router = useRouter()
const notiOpen = ref(false)

onMounted(() => {
  if (auth.isLoggedIn) {
    notif.requestPermission()
    notif.startPolling()
  }
})
onBeforeUnmount(() => notif.stopPolling())

// ── 글로벌 검색 단축키 Cmd+K / Ctrl+K ────────────────────────────────────────
const searchOpen = ref(false)
useEventListener(document, 'keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    searchOpen.value = !searchOpen.value
  }
})

// ── 모바일 사이드바 ───────────────────────────────────────────────────────────
const sideOpen = ref(false)

const NAV_ITEMS = [
  { to: '/',          label: '홈', icon: '🏠' },
  { to: '/stocks',    label: '종목 추천', icon: '📈' },
  { to: '/screener',  label: '스크리너', icon: '🔎' },
  { to: '/sectors',   label: '섹터 맵', icon: '🗺️' },
  { to: '/portfolio', label: '포트폴리오', icon: '💼' },
  { to: '/ranking',   label: '랭킹', icon: '🏆' },
  { to: '/news',      label: '뉴스', icon: '📰' },
  { to: '/compare',   label: '비교', icon: '⚖️' },
  { to: '/board',     label: '커뮤니티', icon: '💬' },
]

function handleLogout() {
  auth.logout()
  sideOpen.value = false
  router.push('/login')
}
</script>

<template>
  <div
    id="app"
    class="min-h-screen flex flex-col transition-colors duration-200"
    :class="theme.isDark ? 'bg-[#0F1117] text-[#E4E6EF]' : 'bg-[#F5F6F8] text-gray-900'"
  >

    <!-- ── 상단 네비게이션 ───────────────────────────────────── -->
    <header
      class="sticky top-0 z-50 border-b transition-colors duration-200"
      :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
    >
      <div class="max-w-7xl mx-auto px-4 h-14 flex items-center gap-3">

        <!-- 햄버거 (모바일) -->
        <button
          class="md:hidden w-8 h-8 flex items-center justify-center rounded-lg transition-colors"
          :class="theme.isDark ? 'text-gray-400 hover:bg-white/10' : 'text-gray-500 hover:bg-gray-100'"
          @click="sideOpen = true"
        >
          ☰
        </button>

        <!-- 로고 -->
        <RouterLink to="/" class="font-bold text-base shrink-0" :class="theme.isDark ? 'text-white' : 'text-gray-900'">
          WP_Capstone
        </RouterLink>

        <!-- 데스크톱 메뉴 -->
        <nav class="hidden md:flex items-center gap-1 flex-1">
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

        <!-- 우측 -->
        <div class="ml-auto flex items-center gap-2 shrink-0">

          <!-- 알림 벨 -->
          <div v-if="auth.isLoggedIn" class="relative">
            <button
              class="relative w-8 h-8 flex items-center justify-center rounded-lg transition-colors"
              :class="theme.isDark ? 'text-gray-400 hover:bg-white/10' : 'text-gray-500 hover:bg-gray-100'"
              @click="notiOpen = !notiOpen; notif.markAllRead()"
            >
              🔔
              <span
                v-if="notif.unread > 0"
                class="absolute top-0.5 right-0.5 w-4 h-4 rounded-full text-[10px] font-bold flex items-center justify-center bg-red-500 text-white"
              >{{ Math.min(notif.unread, 9) }}</span>
            </button>

            <!-- 알림 드롭다운 -->
            <Transition name="search-fade">
              <div
                v-if="notiOpen"
                class="absolute right-0 top-10 w-72 rounded-xl shadow-xl z-50 overflow-hidden"
                :class="theme.isDark ? 'bg-[#1A1D27] border border-[#2A2D3A]' : 'bg-white border border-gray-100'"
              >
                <div class="px-4 py-3 border-b text-sm font-semibold" :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'">알림</div>
                <div v-if="!notif.list.length" class="px-4 py-6 text-center text-sm" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
                  새 알림이 없습니다
                </div>
                <div v-else class="max-h-60 overflow-y-auto">
                  <div
                    v-for="n in notif.list"
                    :key="n.id"
                    class="px-4 py-3 border-b text-sm"
                    :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-50'"
                  >
                    <p class="font-medium">{{ n.title ?? n.message }}</p>
                    <p v-if="n.body" class="text-xs mt-0.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">{{ n.body }}</p>
                  </div>
                </div>
              </div>
            </Transition>
          </div>

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

          <!-- 다크 토글 -->
          <button
            class="w-8 h-8 flex items-center justify-center rounded-lg text-base transition-colors"
            :class="theme.isDark ? 'text-yellow-400 hover:bg-white/10' : 'text-gray-500 hover:bg-gray-100'"
            :title="theme.isDark ? '라이트 모드' : '다크 모드'"
            @click="theme.toggleDark()"
          >
            {{ theme.isDark ? '☀️' : '🌙' }}
          </button>

          <!-- 데스크톱 로그인 -->
          <template v-if="auth.isLoggedIn">
            <RouterLink
              to="/my"
              class="hidden sm:block text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-300 hover:text-white' : 'text-gray-700 hover:text-gray-900'"
            >
              {{ auth.nickname }}
            </RouterLink>
            <button
              class="hidden sm:block text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'"
              @click="handleLogout"
            >
              로그아웃
            </button>
          </template>
          <template v-else>
            <RouterLink
              to="/login"
              class="hidden sm:block text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'"
            >
              로그인
            </RouterLink>
            <RouterLink
              to="/register"
              class="hidden sm:block text-sm px-3 py-1.5 rounded-md transition-colors"
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

    <!-- ── 모바일 하단 탭 바 ───────────────────────────────────── -->
    <nav
      class="md:hidden fixed bottom-0 left-0 right-0 z-40 border-t flex transition-colors duration-200"
      :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
    >
      <RouterLink
        v-for="item in NAV_ITEMS.slice(0, 5)"
        :key="item.to"
        :to="item.to"
        class="flex-1 flex flex-col items-center justify-center py-2 text-[10px] transition-colors"
        :class="theme.isDark ? 'text-gray-600 [&.router-link-active]:text-white' : 'text-gray-400 [&.router-link-active]:text-gray-900'"
        active-class="router-link-active"
        exact-active-class=""
      >
        <span class="text-lg leading-none mb-0.5">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

  </div>

  <!-- ── 모바일 슬라이드 사이드바 ────────────────────────────── -->
  <Transition name="slide">
    <div v-if="sideOpen" class="fixed inset-0 z-[60] md:hidden">
      <!-- 백드롭 -->
      <div class="absolute inset-0 bg-black/50" @click="sideOpen = false" />
      <!-- 패널 -->
      <aside
        class="absolute left-0 top-0 bottom-0 w-72 flex flex-col transition-colors duration-200"
        :class="theme.isDark ? 'bg-[#1A1D27]' : 'bg-white'"
      >
        <!-- 상단 -->
        <div
          class="flex items-center justify-between px-5 h-14 border-b shrink-0"
          :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'"
        >
          <span class="font-bold" :class="theme.isDark ? 'text-white' : 'text-gray-900'">WP_Capstone</span>
          <button
            class="w-8 h-8 flex items-center justify-center rounded-lg"
            :class="theme.isDark ? 'text-gray-400 hover:bg-white/10' : 'text-gray-500 hover:bg-gray-100'"
            @click="sideOpen = false"
          >✕</button>
        </div>

        <!-- 메뉴 -->
        <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <RouterLink
            v-for="item in NAV_ITEMS"
            :key="item.to"
            :to="item.to"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors"
            :class="theme.isDark
              ? 'text-gray-400 hover:text-white hover:bg-white/10 [&.router-link-active]:text-white [&.router-link-active]:bg-white/10 [&.router-link-active]:font-medium'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 [&.router-link-active]:text-gray-900 [&.router-link-active]:bg-gray-100 [&.router-link-active]:font-medium'"
            active-class="router-link-active"
            exact-active-class=""
            @click="sideOpen = false"
          >
            <span class="text-lg">{{ item.icon }}</span>
            {{ item.label }}
          </RouterLink>
        </nav>

        <!-- 하단 로그인 -->
        <div
          class="px-3 pb-6 pt-3 border-t space-y-2"
          :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'"
        >
          <template v-if="auth.isLoggedIn">
            <RouterLink
              to="/my"
              class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-300 hover:bg-white/10' : 'text-gray-700 hover:bg-gray-50'"
              @click="sideOpen = false"
            >
              <span class="text-lg">👤</span> {{ auth.nickname }}
            </RouterLink>
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-500 hover:bg-white/10' : 'text-gray-400 hover:bg-gray-50'"
              @click="handleLogout"
            >
              <span class="text-lg">🚪</span> 로그아웃
            </button>
          </template>
          <template v-else>
            <RouterLink
              to="/login"
              class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors"
              :class="theme.isDark ? 'text-gray-300 hover:bg-white/10' : 'text-gray-700 hover:bg-gray-50'"
              @click="sideOpen = false"
            >
              <span class="text-lg">🔑</span> 로그인
            </RouterLink>
            <RouterLink
              to="/register"
              class="flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors"
              :class="theme.isDark ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-gray-900 text-white hover:bg-gray-700'"
              @click="sideOpen = false"
            >
              회원가입
            </RouterLink>
          </template>
        </div>
      </aside>
    </div>
  </Transition>

  <!-- ── 글로벌 검색 모달 ─────────────────────────────────────── -->
  <Transition name="search-fade">
    <GlobalSearch v-if="searchOpen" @close="searchOpen = false" />
  </Transition>
</template>

<style scoped>
.search-fade-enter-active, .search-fade-leave-active { transition: opacity 0.15s; }
.search-fade-enter-from, .search-fade-leave-to { opacity: 0; }

.slide-enter-active, .slide-leave-active { transition: opacity 0.2s; }
.slide-enter-from, .slide-leave-to { opacity: 0; }
.slide-enter-active aside, .slide-leave-active aside { transition: transform 0.2s ease; }
.slide-enter-from aside, .slide-leave-to aside { transform: translateX(-100%); }
</style>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme.js'
import { useAuthStore }  from '@/stores/auth.js'
import api from '@/api/axios.js'
import TierBadge from '@/components/common/TierBadge.vue'

const route  = useRoute()
const router = useRouter()
const theme  = useThemeStore()
const auth   = useAuthStore()

const nickname = route.params.nickname
const loading  = ref(true)
const error    = ref(null)
const profile  = ref(null)
const posts    = ref([])
const watchlist = ref([])
const following = ref(false)

async function fetchProfile() {
  loading.value = true
  error.value   = null
  try {
    const { data } = await api.get(`/users/${nickname}/public`)
    profile.value   = data
    posts.value     = data.recent_posts ?? []
    watchlist.value = data.public_watchlist ?? []
    following.value = data.is_following ?? false
  } catch (e) {
    if (e?.response?.status === 404) error.value = '존재하지 않는 사용자입니다.'
    else error.value = '프로필을 불러오지 못했습니다.'
    // 모의 데이터
    profile.value = {
      nickname,
      joined_at: '2024-01-15T00:00:00Z',
      post_count: 12,
      follower_count: 34,
      following_count: 18,
      bio: '주식 투자 3년차. IT/헬스케어 섹터 관심.',
    }
    posts.value = Array.from({ length: 5 }, (_, i) => ({
      id: i + 1,
      ticker: ['005930', '000660', '035420'][i % 3],
      title: `${['삼성전자', 'SK하이닉스', 'NAVER'][i % 3]} 투자 의견 ${i + 1}`,
      created_at: new Date(Date.now() - i * 86400000).toISOString(),
      likes: Math.floor(Math.random() * 20),
    }))
    watchlist.value = [
      { ticker: '005930', name: '삼성전자', tier: 'A', score: 78 },
      { ticker: '000660', name: 'SK하이닉스', tier: 'A', score: 75 },
      { ticker: '035420', name: 'NAVER', tier: 'B', score: 65 },
    ]
  } finally {
    loading.value = false
  }
}

async function toggleFollow() {
  if (!auth.isLoggedIn) { router.push('/login'); return }
  try {
    if (following.value) {
      await api.delete(`/users/${nickname}/follow`)
      following.value = false
      if (profile.value) profile.value.follower_count--
    } else {
      await api.post(`/users/${nickname}/follow`)
      following.value = true
      if (profile.value) profile.value.follower_count++
    }
  } catch {
    following.value = !following.value
  }
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
}

const isMe = auth.nickname === nickname

onMounted(fetchProfile)
</script>

<template>
  <div class="max-w-2xl mx-auto px-4 py-4 md:py-6 pb-20 md:pb-6">

    <!-- 로딩 -->
    <div v-if="loading" class="flex justify-center py-20">
      <div class="w-8 h-8 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
    </div>

    <template v-else>

      <!-- 에러 배너 -->
      <div
        v-if="error"
        class="rounded-xl px-4 py-3 mb-4 text-sm"
        :class="theme.isDark ? 'bg-orange-900/20 text-orange-400' : 'bg-orange-50 text-orange-700'"
      >
        ⚠️ {{ error }} (모의 데이터 표시 중)
      </div>

      <!-- 프로필 헤더 -->
      <div
        class="rounded-2xl p-6 mb-5 border"
        :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-center gap-4">
            <div
              class="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold shrink-0"
              :class="theme.isDark ? 'bg-white/10 text-white' : 'bg-gray-100 text-gray-600'"
            >
              {{ nickname?.[0]?.toUpperCase() }}
            </div>
            <div>
              <h1 class="text-xl font-bold">{{ profile?.nickname ?? nickname }}</h1>
              <p v-if="profile?.bio" class="text-sm mt-1" :class="theme.isDark ? 'text-gray-400' : 'text-gray-600'">
                {{ profile.bio }}
              </p>
              <p class="text-xs mt-1.5" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">
                가입: {{ formatDate(profile?.joined_at) }}
              </p>
            </div>
          </div>

          <!-- 팔로우 버튼 -->
          <button
            v-if="!isMe"
            class="shrink-0 px-4 py-1.5 rounded-xl text-sm font-medium transition-colors"
            :class="following
              ? (theme.isDark ? 'bg-white/10 text-gray-400 hover:bg-red-900/30 hover:text-red-400' : 'bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-500')
              : (theme.isDark ? 'bg-indigo-600 text-white hover:bg-indigo-500' : 'bg-indigo-600 text-white hover:bg-indigo-700')"
            @click="toggleFollow"
          >
            {{ following ? '팔로잉 ✓' : '팔로우' }}
          </button>
        </div>

        <!-- 통계 -->
        <div class="grid grid-cols-3 gap-3 mt-5 pt-5 border-t" :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'">
          <div class="text-center">
            <p class="text-xl font-bold">{{ profile?.post_count ?? posts.length }}</p>
            <p class="text-xs mt-0.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">게시글</p>
          </div>
          <div class="text-center">
            <p class="text-xl font-bold">{{ profile?.follower_count ?? 0 }}</p>
            <p class="text-xs mt-0.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">팔로워</p>
          </div>
          <div class="text-center">
            <p class="text-xl font-bold">{{ profile?.following_count ?? 0 }}</p>
            <p class="text-xs mt-0.5" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">팔로잉</p>
          </div>
        </div>
      </div>

      <!-- 공개 관심 종목 -->
      <div
        v-if="watchlist.length"
        class="rounded-2xl overflow-hidden mb-5 border"
        :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
      >
        <div class="px-5 py-4 border-b" :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'">
          <h2 class="font-semibold text-sm">공개 관심 종목</h2>
        </div>
        <div class="divide-y" :class="theme.isDark ? 'divide-[#2A2D3A]' : 'divide-gray-50'">
          <div
            v-for="s in watchlist"
            :key="s.ticker"
            class="flex items-center gap-3 px-5 py-3 cursor-pointer transition-colors"
            :class="theme.isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'"
            @click="router.push('/stocks/' + s.ticker)"
          >
            <TierBadge :tier="s.tier" />
            <div class="flex-1">
              <span class="text-sm font-medium">{{ s.name }}</span>
              <span class="text-xs ml-2" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">{{ s.ticker }}</span>
            </div>
            <span class="text-sm font-semibold">{{ s.score }}점</span>
          </div>
        </div>
      </div>

      <!-- 최근 게시글 -->
      <div
        class="rounded-2xl overflow-hidden border"
        :class="theme.isDark ? 'bg-[#1A1D27] border-[#2A2D3A]' : 'bg-white border-gray-100'"
      >
        <div class="px-5 py-4 border-b" :class="theme.isDark ? 'border-[#2A2D3A]' : 'border-gray-100'">
          <h2 class="font-semibold text-sm">최근 게시글</h2>
        </div>
        <div v-if="!posts.length" class="px-5 py-8 text-center text-sm" :class="theme.isDark ? 'text-gray-500' : 'text-gray-400'">
          작성한 게시글이 없습니다
        </div>
        <div v-else class="divide-y" :class="theme.isDark ? 'divide-[#2A2D3A]' : 'divide-gray-50'">
          <div
            v-for="post in posts"
            :key="post.id"
            class="flex items-center gap-3 px-5 py-3.5 cursor-pointer transition-colors"
            :class="theme.isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'"
            @click="router.push('/board?id=' + post.id)"
          >
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium truncate">{{ post.title }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span class="text-xs" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">{{ post.ticker }}</span>
                <span class="text-xs" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">{{ formatDate(post.created_at) }}</span>
              </div>
            </div>
            <span class="text-xs shrink-0" :class="theme.isDark ? 'text-gray-600' : 'text-gray-400'">
              ♥ {{ post.likes }}
            </span>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

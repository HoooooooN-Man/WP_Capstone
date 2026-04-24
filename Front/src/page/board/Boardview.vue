<!-- front/board/BoardView.vue -->
<!-- WP_Capstone — P-07 커뮤니티 게시판 목록 -->

<template>
  <div class="board-wrap">
    <!-- 종목 헤더 배너 -->
    <div class="board-header">
      <div class="board-header__info">
        <span class="board-header__ticker">{{ ticker }}</span>
        <span class="board-header__title">커뮤니티 게시판</span>
      </div>
      <router-link :to="`/stocks/${ticker}`" class="board-header__link">
        종목 상세 →
      </router-link>
    </div>

    <!-- 작성 버튼 -->
    <div class="board-toolbar">
      <span class="board-toolbar__count">전체 {{ store.total }}개</span>
      <button class="btn btn--primary" @click="onClickWrite">글쓰기</button>
    </div>

    <!-- 로딩 -->
    <div v-if="store.loading" class="board-loading">불러오는 중...</div>

    <!-- 에러 -->
    <div v-else-if="store.error" class="board-error">
      {{ store.error }}
      <button class="btn btn--ghost" @click="loadPosts">재시도</button>
    </div>

    <!-- 게시글 목록 -->
    <template v-else>
      <div v-if="store.posts.length === 0" class="board-empty">
        첫 번째 게시글을 작성해보세요!
      </div>

      <ul v-else class="post-list">
        <li
          v-for="post in store.posts"
          :key="post.id"
          class="post-item"
          @click="openDetail(post.id)"
        >
          <div class="post-item__main">
            <span class="post-item__title">{{ post.title }}</span>
          </div>
          <div class="post-item__meta">
            <span>작성자 #{{ post.author_id }}</span>
            <span>조회 {{ post.views }}</span>
            <span class="post-item__like" @click.stop="onLike(post.id)">
              <span :class="['heart', { 'heart--filled': post.liked }]">♥</span>
              {{ post.likes }}
            </span>
            <span>댓글 {{ post.comment_count }}</span>
            <span>{{ formatDate(post.created_at) }}</span>
          </div>
        </li>
      </ul>

      <!-- 페이지네이션 -->
      <div class="pagination">
        <button
          class="btn btn--ghost"
          :disabled="store.page <= 1"
          @click="changePage(store.page - 1)"
        >이전</button>
        <span class="pagination__info">{{ store.page }} / {{ store.totalPages }}</span>
        <button
          class="btn btn--ghost"
          :disabled="store.page >= store.totalPages"
          @click="changePage(store.page + 1)"
        >다음</button>
      </div>
    </template>

    <!-- 게시글 작성 모달 -->
    <PostFormModal
      v-if="showWriteModal"
      :ticker="ticker"
      @close="showWriteModal = false"
      @submitted="onPostSubmitted"
    />

    <!-- 게시글 상세 모달 -->
    <PostDetailModal
      v-if="activePostId !== null"
      :post-id="activePostId"
      @close="activePostId = null"
      @deleted="onPostDeleted"
    />

    <!-- 로그인 유도 모달 -->
    <LoginPromptModal v-if="showLoginPrompt" @close="showLoginPrompt = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBoardStore } from '@/stores/boardStore'
import { useAuthStore } from '@/stores/auth'
import PostFormModal from '@/page/board/PostFormModal.vue'
import PostDetailModal from '@/page/board/PostDetailModal.vue'
import LoginPromptModal from '@/page/board/LoginPromptModal.vue'

const route = useRoute()
const router = useRouter()
const store = useBoardStore()
const auth = useAuthStore()

const ticker = ref(String(route.params.ticker ?? ''))
const showWriteModal = ref(false)
const showLoginPrompt = ref(false)
const activePostId = ref<number | null>(null)

async function loadPosts(page?: number) {
  // 인자가 없거나 숫자가 아니면(이벤트 객체면) 스토어의 현재 페이지 사용
  const targetPage = (typeof page === 'number') ? page : store.page;
  await store.fetchPosts(ticker.value, targetPage);
}

function changePage(p: number) {
  if (p < 1 || p > store.totalPages) return; // 페이지 범위 방어 코드 추가
  loadPosts(p);
}

function openDetail(id: number) {
  activePostId.value = id
}

function onClickWrite() {
  if (!auth.isLoggedIn) {
    showLoginPrompt.value = true
    return
  }
  showWriteModal.value = true
}

async function onLike(postId: number) {
  if (!auth.isLoggedIn) {
    showLoginPrompt.value = true
    return
  }
  await store.toggleLike(postId)
}

function onPostSubmitted() {
  showWriteModal.value = false
  loadPosts(1)
}

function onPostDeleted() {
  activePostId.value = null
  loadPosts(store.page)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('ko-KR', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

// ticker가 URL로 바뀌면 재조회
watch(() => route.params.ticker, (val) => {
  if (val) {
    ticker.value = String(val)
    loadPosts(1)
  }
})

onMounted(() => loadPosts(1))
</script>

<style scoped>
/* ── 레이아웃 ───────────────────────────────────────────── */
.board-wrap {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 16px;
  font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif;
}

/* ── 헤더 배너 ──────────────────────────────────────────── */
.board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 20px;
  margin-bottom: 16px;
}
.board-header__info { display: flex; align-items: center; gap: 10px; }
.board-header__ticker {
  font-size: 18px;
  font-weight: 700;
  color: #1e40af;
}
.board-header__title { font-size: 15px; color: #475569; }
.board-header__link {
  font-size: 13px;
  color: #6366f1;
  text-decoration: none;
}
.board-header__link:hover { text-decoration: underline; }

/* ── 툴바 ──────────────────────────────────────────────── */
.board-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.board-toolbar__count { font-size: 13px; color: #64748b; }

/* ── 버튼 ──────────────────────────────────────────────── */
.btn {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  transition: background 0.15s;
}
.btn--primary { background: #6366f1; color: #fff; }
.btn--primary:hover { background: #4f46e5; }
.btn--ghost {
  background: transparent;
  color: #475569;
  border: 1px solid #cbd5e1;
}
.btn--ghost:hover { background: #f1f5f9; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── 목록 ──────────────────────────────────────────────── */
.post-list { list-style: none; margin: 0; padding: 0; }

.post-item {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
  transition: background 0.12s;
}
.post-item:hover { background: #f8fafc; }

.post-item__title {
  font-size: 15px;
  font-weight: 500;
  color: #1e293b;
}

.post-item__meta {
  display: flex;
  gap: 14px;
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
}

/* ── 좋아요 하트 ─────────────────────────────────────────── */
.post-item__like { display: flex; align-items: center; gap: 3px; cursor: pointer; }
.heart { color: #cbd5e1; transition: color 0.15s; }
.heart--filled { color: #ef4444; }

/* ── 페이지네이션 ─────────────────────────────────────────── */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}
.pagination__info { font-size: 13px; color: #64748b; }

/* ── 로딩 / 에러 / 빈 상태 ────────────────────────────────── */
.board-loading,
.board-empty {
  text-align: center;
  padding: 48px 0;
  color: #94a3b8;
  font-size: 14px;
}
.board-error {
  text-align: center;
  padding: 32px;
  color: #ef4444;
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
</style>
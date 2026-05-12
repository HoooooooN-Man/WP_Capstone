<!-- front/board/BoardView.vue -->
<!-- WP_Capstone - 종목 커뮤니티 게시판 목록 -->

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

    <!-- 글쓰기 버튼 -->
    <div class="board-toolbar">
      <span class="board-toolbar__count">전체 {{ store.total }}개</span>
      <button class="btn btn--primary" @click="onClickWrite">글쓰기</button>
    </div>

    <!-- 로딩 -->
    <div v-if="store.loading" class="board-loading">불러오는 중...</div>

    <!-- 에러 -->
    <div v-else-if="store.error" class="board-error">
      {{ store.error }}
      <button class="btn btn--ghost" @click="loadPosts">다시 시도</button>
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
// @ts-nocheck
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
  const targetPage = (typeof page === 'number') ? page : store.page
  await store.fetchPosts(ticker.value, targetPage)
}

function changePage(p: number) {
  if (p < 1 || p > store.totalPages) return
  loadPosts(p)
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

// ticker가 URL로 변경되면 재조회
watch(() => route.params.ticker, (val) => {
  if (val) {
    ticker.value = String(val)
    loadPosts(1)
  }
})

onMounted(() => loadPosts(1))
</script>

<style scoped>
/* UX W7A — BoardView 토큰 적용. template·script 변경 0. */

.board-wrap {
  max-width: 860px;
  margin: 0 auto;
  padding: var(--space-6) var(--layout-content-pad);
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.board-header {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--surface-muted);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-5);
  margin-bottom: var(--space-4);
}
.board-header__info { display: flex; align-items: center; gap: var(--space-2); }
.board-header__ticker {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-primary-700);
}
.board-header__title {
  font-size: var(--text-base);
  color: var(--text-secondary);
}
.board-header__link {
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  text-decoration: none;
}
.board-header__link:hover { text-decoration: underline; }

.board-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: var(--space-3);
}
.board-toolbar__count {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.btn {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background var(--duration-fast) var(--ease-out);
}
.btn--primary {
  background: var(--color-primary-600);
  color: var(--text-inverse);
  border-color: var(--color-primary-600);
}
.btn--primary:hover { background: var(--color-primary-700); }
.btn--ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: var(--border-default);
}
.btn--ghost:hover { background: var(--surface-muted); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.post-list { list-style: none; margin: 0; padding: 0; }

.post-item {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.post-item:hover { background: var(--surface-muted); }
.post-item__title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.post-item__meta {
  display: flex; gap: var(--space-3);
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

/* 좋아요 — 한국 관례 빨강 (--color-up). */
.post-item__like {
  display: flex; align-items: center; gap: 3px;
  cursor: pointer;
}
.heart {
  color: var(--border-default);
  transition: color var(--duration-fast) var(--ease-out);
}
.heart--filled { color: var(--color-up); }

.pagination {
  display: flex; justify-content: center; align-items: center;
  gap: var(--space-4);
  margin-top: var(--space-6);
}
.pagination__info {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.board-loading,
.board-empty {
  text-align: center;
  padding: var(--space-12) 0;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}
.board-error {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-danger);
  font-size: var(--text-sm);
  display: flex; flex-direction: column; align-items: center; gap: var(--space-3);
}

/* UX W8D — 태블릿 적응 (≤768px). 모바일 풀 대응은 컷 (W9 박제). */
@media (max-width: 768px) {
  .board-wrap { padding: var(--space-4) var(--space-3); }
  .board-header { flex-wrap: wrap; gap: var(--space-2); padding: var(--space-3); }
  .board-header__info { flex-wrap: wrap; }
  .post-item { padding: var(--space-3); }
  .post-item__meta { flex-wrap: wrap; gap: var(--space-2); }
  .pagination { gap: var(--space-2); }
}
</style>

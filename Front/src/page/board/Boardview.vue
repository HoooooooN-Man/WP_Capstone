<!-- front/board/BoardView.vue -->
<!-- WP_Capstone ??P-07 而ㅻ??덊떚 寃뚯떆??紐⑸줉 -->

<template>
  <div class="board-wrap">
    <!-- 醫낅ぉ ?ㅻ뜑 諛곕꼫 -->
    <div class="board-header">
      <div class="board-header__info">
        <span class="board-header__ticker">{{ ticker }}</span>
        <span class="board-header__title">而ㅻ??덊떚 寃뚯떆??/span>
      </div>
      <router-link :to="`/stocks/${ticker}`" class="board-header__link">
        醫낅ぉ ?곸꽭 ??
      </router-link>
    </div>

    <!-- ?묒꽦 踰꾪듉 -->
    <div class="board-toolbar">
      <span class="board-toolbar__count">?꾩껜 {{ store.total }}媛?/span>
      <button class="btn btn--primary" @click="onClickWrite">湲?곌린</button>
    </div>

    <!-- 濡쒕뵫 -->
    <div v-if="store.loading" class="board-loading">遺덈윭?ㅻ뒗 以?..</div>

    <!-- ?먮윭 -->
    <div v-else-if="store.error" class="board-error">
      {{ store.error }}
      <button class="btn btn--ghost" @click="loadPosts">?ъ떆??/button>
    </div>

    <!-- 寃뚯떆湲 紐⑸줉 -->
    <template v-else>
      <div v-if="store.posts.length === 0" class="board-empty">
        泥?踰덉㎏ 寃뚯떆湲???묒꽦?대낫?몄슂!
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
            <span>?묒꽦??#{{ post.author_id }}</span>
            <span>議고쉶 {{ post.views }}</span>
            <span class="post-item__like" @click.stop="onLike(post.id)">
              <span :class="['heart', { 'heart--filled': post.liked }]">??/span>
              {{ post.likes }}
            </span>
            <span>?볤? {{ post.comment_count }}</span>
            <span>{{ formatDate(post.created_at) }}</span>
          </div>
        </li>
      </ul>

      <!-- ?섏씠吏?ㅼ씠??-->
      <div class="pagination">
        <button
          class="btn btn--ghost"
          :disabled="store.page <= 1"
          @click="changePage(store.page - 1)"
        >?댁쟾</button>
        <span class="pagination__info">{{ store.page }} / {{ store.totalPages }}</span>
        <button
          class="btn btn--ghost"
          :disabled="store.page >= store.totalPages"
          @click="changePage(store.page + 1)"
        >?ㅼ쓬</button>
      </div>
    </template>

    <!-- 寃뚯떆湲 ?묒꽦 紐⑤떖 -->
    <PostFormModal
      v-if="showWriteModal"
      :ticker="ticker"
      @close="showWriteModal = false"
      @submitted="onPostSubmitted"
    />

    <!-- 寃뚯떆湲 ?곸꽭 紐⑤떖 -->
    <PostDetailModal
      v-if="activePostId !== null"
      :post-id="activePostId"
      @close="activePostId = null"
      @deleted="onPostDeleted"
    />

    <!-- 濡쒓렇???좊룄 紐⑤떖 -->
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
  // ?몄옄媛 ?녾굅???レ옄媛 ?꾨땲硫??대깽??媛앹껜硫? ?ㅽ넗?댁쓽 ?꾩옱 ?섏씠吏 ?ъ슜
  const targetPage = (typeof page === 'number') ? page : store.page;
  await store.fetchPosts(ticker.value, targetPage);
}

function changePage(p: number) {
  if (p < 1 || p > store.totalPages) return; // ?섏씠吏 踰붿쐞 諛⑹뼱 肄붾뱶 異붽?
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

// ticker媛 URL濡?諛붾뚮㈃ ?ъ“??
watch(() => route.params.ticker, (val) => {
  if (val) {
    ticker.value = String(val)
    loadPosts(1)
  }
})

onMounted(() => loadPosts(1))
</script>

<style scoped>
/* ?? ?덉씠?꾩썐 ????????????????????????????????????????????? */
.board-wrap {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 16px;
  font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif;
}

/* ?? ?ㅻ뜑 諛곕꼫 ???????????????????????????????????????????? */
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

/* ?? ?대컮 ???????????????????????????????????????????????? */
.board-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.board-toolbar__count { font-size: 13px; color: #64748b; }

/* ?? 踰꾪듉 ???????????????????????????????????????????????? */
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

/* ?? 紐⑸줉 ???????????????????????????????????????????????? */
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

/* ?? 醫뗭븘???섑듃 ??????????????????????????????????????????? */
.post-item__like { display: flex; align-items: center; gap: 3px; cursor: pointer; }
.heart { color: #cbd5e1; transition: color 0.15s; }
.heart--filled { color: #ef4444; }

/* ?? ?섏씠吏?ㅼ씠????????????????????????????????????????????? */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}
.pagination__info { font-size: 13px; color: #64748b; }

/* ?? 濡쒕뵫 / ?먮윭 / 鍮??곹깭 ?????????????????????????????????? */
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
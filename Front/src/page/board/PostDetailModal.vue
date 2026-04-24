<!-- front/board/PostDetailModal.vue -->
<!-- 寃뚯떆湲 ?곸꽭 紐⑤떖 (?볤?, 醫뗭븘?? ??젣 ?ы븿) -->

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <!-- ?ㅻ뜑 -->
      <div class="modal__header">
        <h3 class="modal__title">{{ post?.title }}</h3>
        <button class="modal__close" @click="$emit('close')">??/button>
      </div>

      <!-- 濡쒕뵫 -->
      <div v-if="loading" class="detail-loading">遺덈윭?ㅻ뒗 以?..</div>

      <template v-else-if="post">
        <!-- 硫뷀? -->
        <div class="detail-meta">
          <span>?묒꽦??#{{ post.author_id }}</span>
          <span>議고쉶 {{ post.views }}</span>
          <span>{{ formatDate(post.created_at) }}</span>
          <!-- 蹂몄씤 湲 ??젣 踰꾪듉 -->
          <button
            v-if="isAuthor"
            class="btn btn--danger btn--sm"
            @click="confirmDelete"
          >??젣</button>
        </div>

        <!-- 蹂몃Ц -->
        <div class="detail-content">{{ post.content }}</div>

        <!-- 醫뗭븘??-->
        <div class="detail-like">
          <button
            :class="['like-btn', { 'like-btn--active': post.liked }]"
            @click="onLike"
          >
            ??{{ post.likes }}
          </button>
        </div>

        <!-- ?볤? 紐⑸줉 -->
        <div class="comment-section">
          <p class="comment-section__title">?볤? {{ post.comments.length }}媛?/p>
          <ul class="comment-list">
            <li v-for="c in post.comments" :key="c.id" class="comment-item">
              <span class="comment-item__author">#{{ c.author_id }}</span>
              <span class="comment-item__content">{{ c.content }}</span>
              <span class="comment-item__date">{{ formatDate(c.created_at) }}</span>
            </li>
          </ul>

          <!-- ?볤? ?묒꽦 -->
          <div v-if="auth.isLoggedIn" class="comment-form">
            <textarea
              v-model="commentText"
              class="comment-form__input"
              rows="3"
              placeholder="?볤????낅젰?섏꽭??
            />
            <button
              class="btn btn--primary btn--sm"
              :disabled="submittingComment"
              @click="submitComment"
            >
              {{ submittingComment ? '?깅줉 以?..' : '?볤? ?깅줉' }}
            </button>
          </div>
          <p v-else class="comment-login-hint">
            ?볤????묒꽦?섎젮硫?
            <router-link to="/login">濡쒓렇??/router-link>???꾩슂?⑸땲??
          </p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref, computed, onMounted } from 'vue'
import { useBoardStore } from '@/stores/boardStore'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ postId: number }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'deleted'): void
}>()

const store = useBoardStore()
const auth = useAuthStore()

const loading = ref(false)
const commentText = ref('')
const submittingComment = ref(false)

const post = computed(() => store.postCache[props.postId] ?? null)
const isAuthor = computed(
  () => auth.isLoggedIn && post.value?.author_id === Number((auth.sessionToken ?? '').split('_')[1])
)

async function loadDetail() {
  if (store.postCache[props.postId]) return
  loading.value = true
  try {
    await store.fetchPostDetail(props.postId)
  } finally {
    loading.value = false
  }
}

async function onLike() {
  if (!auth.isLoggedIn) {
    alert('濡쒓렇?몄씠 ?꾩슂?⑸땲??')
    return
  }
  await store.toggleLike(props.postId)
}

async function submitComment() {
  if (!commentText.value.trim()) return
  submittingComment.value = true
  try {
    await store.createComment(props.postId, commentText.value.trim())
    commentText.value = ''
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? '?볤? ?깅줉???ㅽ뙣?덉뒿?덈떎.')
  } finally {
    submittingComment.value = false
  }
}

async function confirmDelete() {
  if (!confirm('寃뚯떆湲????젣?섏떆寃좎뒿?덇퉴?')) return
  try {
    await store.deletePost(props.postId)
    emit('deleted')
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? '??젣???ㅽ뙣?덉뒿?덈떎.')
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(loadDetail)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: #fff;
  border-radius: 12px;
  width: 640px;
  max-width: 96vw;
  max-height: 88vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  display: flex;
  flex-direction: column;
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 18px 20px 12px;
  border-bottom: 1px solid #f1f5f9;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
}
.modal__title {
  font-size: 17px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  line-height: 1.4;
  flex: 1;
  padding-right: 12px;
}
.modal__close {
  background: none;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  flex-shrink: 0;
}

/* 硫뷀? */
.detail-meta {
  display: flex;
  gap: 14px;
  align-items: center;
  font-size: 12px;
  color: #94a3b8;
  padding: 10px 20px;
  border-bottom: 1px solid #f8fafc;
}

/* 蹂몃Ц */
.detail-content {
  padding: 20px;
  font-size: 15px;
  color: #334155;
  line-height: 1.7;
  white-space: pre-wrap;
  min-height: 80px;
}

/* 醫뗭븘??*/
.detail-like {
  padding: 0 20px 16px;
  display: flex;
  justify-content: center;
}
.like-btn {
  padding: 8px 24px;
  border: 1.5px solid #e2e8f0;
  border-radius: 20px;
  background: #fff;
  font-size: 14px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.15s;
}
.like-btn--active {
  border-color: #ef4444;
  color: #ef4444;
  background: #fff5f5;
}
.like-btn:hover { border-color: #ef4444; color: #ef4444; }

/* ?볤? */
.comment-section {
  border-top: 1px solid #f1f5f9;
  padding: 16px 20px 24px;
}
.comment-section__title {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  margin: 0 0 12px;
}
.comment-list { list-style: none; margin: 0; padding: 0; }
.comment-item {
  display: flex;
  gap: 10px;
  align-items: baseline;
  padding: 8px 0;
  border-bottom: 1px solid #f8fafc;
  font-size: 13px;
}
.comment-item__author { font-weight: 600; color: #6366f1; min-width: 60px; }
.comment-item__content { flex: 1; color: #334155; }
.comment-item__date { color: #cbd5e1; font-size: 11px; white-space: nowrap; }

.comment-form {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.comment-form__input {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
  outline: none;
}
.comment-form__input:focus { border-color: #6366f1; }
.comment-login-hint { font-size: 13px; color: #94a3b8; margin-top: 14px; }
.comment-login-hint a { color: #6366f1; }

/* 踰꾪듉 */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  align-self: flex-end;
}
.btn--sm { padding: 5px 12px; font-size: 12px; }
.btn--primary { background: #6366f1; color: #fff; }
.btn--primary:hover { background: #4f46e5; }
.btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn--danger { background: #fee2e2; color: #ef4444; }
.btn--danger:hover { background: #fecaca; }

.detail-loading {
  padding: 48px;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
}
</style>
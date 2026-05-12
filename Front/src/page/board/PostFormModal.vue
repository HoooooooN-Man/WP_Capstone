<!-- front/board/PostFormModal.vue -->
<!-- 게시글 작성 모달 -->

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal__header">
        <h3 class="modal__title">게시글 작성</h3>
        <button class="modal__close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal__body">
        <label class="form-label">제목</label>
        <input
          v-model="title"
          class="form-input"
          placeholder="제목을 입력하세요"
          maxlength="255"
        />
        <span v-if="errors.title" class="form-error">{{ errors.title }}</span>

        <label class="form-label" style="margin-top:14px;">내용</label>
        <textarea
          v-model="content"
          class="form-textarea"
          placeholder="내용을 입력하세요"
          rows="8"
        />
        <span v-if="errors.content" class="form-error">{{ errors.content }}</span>
      </div>

      <div class="modal__footer">
        <button class="btn btn--ghost" @click="$emit('close')">취소</button>
        <button class="btn btn--primary" :disabled="submitting" @click="submit">
          {{ submitting ? '등록 중...' : '등록' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref, reactive } from 'vue'
import { useBoardStore } from '@/stores/boardStore'

const props = defineProps<{ ticker: string }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'submitted'): void }>()

const store = useBoardStore()
const title = ref('')
const content = ref('')
const submitting = ref(false)
const errors = reactive({ title: '', content: '' })

function validate() {
  errors.title = title.value.trim() ? '' : '제목을 입력해주세요.'
  errors.content = content.value.trim() ? '' : '내용을 입력해주세요.'
  return !errors.title && !errors.content
}

async function submit() {
  if (!validate()) return
  submitting.value = true
  try {
    await store.createPost(props.ticker, title.value.trim(), content.value.trim())
    emit('submitted')
  } catch (e: any) {
    errors.content = e?.response?.data?.detail ?? '등록에 실패했습니다.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
/* UX W7A — 토큰 적용. template·script 변경 0. */
.modal-overlay {
  position: fixed; inset: 0;
  background: var(--surface-overlay);
  display: flex; align-items: center; justify-content: center;
  z-index: var(--z-modal);
  font-family: var(--font-sans);
}
.modal {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  width: 540px; max-width: 95vw;
  box-shadow: var(--shadow-xl);
}
.modal__header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-4) var(--space-5) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
}
.modal__title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}
.modal__close {
  background: none; border: 0;
  font-size: var(--text-lg);
  color: var(--text-tertiary);
  cursor: pointer;
}
.modal__body { padding: var(--space-4) var(--space-5); }
.modal__footer {
  display: flex; justify-content: flex-end; gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--border-subtle);
}

.form-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}
.form-input,
.form-textarea {
  width: 100%; box-sizing: border-box;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: inherit;
  background: var(--surface-card);
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--duration-fast) var(--ease-out),
              box-shadow var(--duration-fast) var(--ease-out);
}
.form-textarea { resize: vertical; }
.form-input:focus,
.form-textarea:focus {
  border-color: var(--border-focus);
  box-shadow: var(--shadow-focus);
}
.form-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
  margin-top: var(--space-1);
  display: block;
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
.btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn--ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: var(--border-default);
}
.btn--ghost:hover { background: var(--surface-muted); }
</style>

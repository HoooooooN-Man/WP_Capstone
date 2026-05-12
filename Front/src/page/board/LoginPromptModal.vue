<!-- front/board/LoginPromptModal.vue -->
<!-- 비로그인 사용자 로그인 유도 모달 -->

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <p class="modal__msg">로그인이 필요한 기능입니다.</p>
      <div class="modal__actions">
        <button class="btn btn--ghost" @click="$emit('close')">취소</button>
        <router-link to="/login" class="btn btn--primary" @click="$emit('close')">
          로그인하기
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{ (e: 'close'): void }>()
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
  padding: var(--space-6) var(--space-8);
  text-align: center;
  box-shadow: var(--shadow-xl);
  min-width: 280px;
}
.modal__msg {
  font-size: var(--text-base);
  color: var(--text-primary);
  margin: 0 0 var(--space-5);
}
.modal__actions {
  display: flex; justify-content: center; gap: var(--space-2);
}
.btn {
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
  border: 1px solid transparent;
  text-decoration: none;
  display: inline-flex; align-items: center;
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
</style>

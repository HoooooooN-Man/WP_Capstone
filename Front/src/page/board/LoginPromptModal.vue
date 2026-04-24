<!-- front/board/LoginPromptModal.vue -->
<!-- 鍮꾨줈洹몄씤 ?묎렐 ??濡쒓렇???좊룄 紐⑤떖 -->

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <p class="modal__msg">濡쒓렇?????댁슜 媛?ν빀?덈떎.</p>
      <div class="modal__actions">
        <button class="btn btn--ghost" @click="$emit('close')">痍⑥냼</button>
        <router-link to="/login" class="btn btn--primary" @click="$emit('close')">
          濡쒓렇?명븯湲?
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{ (e: 'close'): void }>()
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal {
  background: #fff;
  border-radius: 10px;
  padding: 28px 32px;
  text-align: center;
  box-shadow: 0 6px 24px rgba(0,0,0,0.15);
  min-width: 280px;
}
.modal__msg { font-size: 15px; color: #334155; margin: 0 0 20px; }
.modal__actions { display: flex; justify-content: center; gap: 10px; }
.btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn--primary { background: #6366f1; color: #fff; }
.btn--primary:hover { background: #4f46e5; }
.btn--ghost { background: transparent; color: #475569; border: 1px solid #cbd5e1; }
.btn--ghost:hover { background: #f1f5f9; }
</style>
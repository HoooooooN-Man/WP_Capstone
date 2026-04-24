<!-- front/board/PostFormModal.vue -->
<!-- 寃뚯떆湲 ?묒꽦 紐⑤떖 -->

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal__header">
        <h3 class="modal__title">寃뚯떆湲 ?묒꽦</h3>
        <button class="modal__close" @click="$emit('close')">??/button>
      </div>

      <div class="modal__body">
        <label class="form-label">?쒕ぉ</label>
        <input
          v-model="title"
          class="form-input"
          placeholder="?쒕ぉ???낅젰?섏꽭??
          maxlength="255"
        />
        <span v-if="errors.title" class="form-error">{{ errors.title }}</span>

        <label class="form-label" style="margin-top:14px;">?댁슜</label>
        <textarea
          v-model="content"
          class="form-textarea"
          placeholder="?댁슜???낅젰?섏꽭??
          rows="8"
        />
        <span v-if="errors.content" class="form-error">{{ errors.content }}</span>
      </div>

      <div class="modal__footer">
        <button class="btn btn--ghost" @click="$emit('close')">痍⑥냼</button>
        <button class="btn btn--primary" :disabled="submitting" @click="submit">
          {{ submitting ? '?깅줉 以?..' : '?깅줉' }}
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
  errors.title = title.value.trim() ? '' : '?쒕ぉ???낅젰?섏꽭??'
  errors.content = content.value.trim() ? '' : '?댁슜???낅젰?섏꽭??'
  return !errors.title && !errors.content
}

async function submit() {
  if (!validate()) return
  submitting.value = true
  try {
    await store.createPost(props.ticker, title.value.trim(), content.value.trim())
    emit('submitted')
  } catch (e: any) {
    errors.content = e?.response?.data?.detail ?? '?깅줉???ㅽ뙣?덉뒿?덈떎.'
  } finally {
    submitting.value = false
  }
}
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
  width: 540px;
  max-width: 95vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px 12px;
  border-bottom: 1px solid #f1f5f9;
}
.modal__title { font-size: 16px; font-weight: 600; color: #1e293b; margin: 0; }
.modal__close {
  background: none;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
}
.modal__body { padding: 18px 20px; }
.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #f1f5f9;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  margin-bottom: 6px;
}
.form-input {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.15s;
}
.form-input:focus { border-color: #6366f1; }
.form-textarea {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  resize: vertical;
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.15s;
}
.form-textarea:focus { border-color: #6366f1; }
.form-error { font-size: 12px; color: #ef4444; margin-top: 4px; display: block; }

.btn {
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: none;
}
.btn--primary { background: #6366f1; color: #fff; }
.btn--primary:hover { background: #4f46e5; }
.btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn--ghost { background: transparent; color: #475569; border: 1px solid #cbd5e1; }
.btn--ghost:hover { background: #f1f5f9; }
</style>
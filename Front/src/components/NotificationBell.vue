<script setup lang="ts">
// UX W7B — 알림 벨 컴포넌트. App.vue 인라인 → 분리.
// 기존 notifications.js store 재사용. 권한 요청 passive (caller 가 start polling).
// 토큰: surface-card, shadow-xl, color-danger.

import { ref } from 'vue'
import NotificationDropdown from './NotificationDropdown.vue'

// @ts-ignore — 기존 store .js
import { useNotificationStore } from '@/stores/notifications.js'

const notif = useNotificationStore()
const open  = ref(false)

function toggle() {
  open.value = !open.value
  if (open.value) {
    // 토스 패턴 — 드롭다운 열 때 자동 markAllRead. (기존 App.vue 동작 유지)
    notif.markAllRead()
  }
}

function close() { open.value = false }
</script>

<template>
  <div class="notification-bell">
    <button
      class="notification-bell__btn"
      :aria-label="notif.unread > 0 ? `알림 ${notif.unread}건` : '알림'"
      :aria-expanded="open"
      @click="toggle"
    >
      <i class="pi pi-bell" aria-hidden="true" />
      <span
        v-if="notif.unread > 0"
        class="notification-bell__badge"
        :aria-hidden="true"
      >{{ Math.min(notif.unread, 9) }}</span>
    </button>

    <Transition name="bell-fade">
      <div
        v-if="open"
        class="notification-bell__dropdown"
        @click.outside="close"
      >
        <NotificationDropdown :list="notif.list" />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.notification-bell {
  position: relative;
  display: inline-flex;
}
.notification-bell__btn {
  position: relative;
  width: 2rem; height: 2rem;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent;
  border: 0;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: var(--text-base);
  transition: background var(--duration-fast) var(--ease-out);
}
.notification-bell__btn:hover { background: var(--surface-muted); }
.notification-bell__btn:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.notification-bell__badge {
  position: absolute;
  top: 2px; right: 2px;
  width: 16px; height: 16px;
  background: var(--color-danger);
  color: var(--text-inverse);
  font-size: 10px;
  font-weight: var(--font-bold);
  border-radius: var(--radius-full);
  display: inline-flex; align-items: center; justify-content: center;
  line-height: 1;
}

.notification-bell__dropdown {
  position: absolute;
  right: 0; top: 2.5rem;
  z-index: var(--z-dropdown);
}

.bell-fade-enter-active,
.bell-fade-leave-active { transition: opacity var(--duration-fast) var(--ease-out); }
.bell-fade-enter-from,
.bell-fade-leave-to     { opacity: 0; }
</style>

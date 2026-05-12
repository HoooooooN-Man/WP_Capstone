<script setup lang="ts">
// UX W7B — 알림 드롭다운. NotificationBell 가 클릭 시 렌더.
// 단순 표시 — store 의존 X (caller 가 list prop 전달).

interface NotificationItem {
  id?: string | number
  title?: string
  message?: string
  body?: string
}

defineProps<{
  list: NotificationItem[]
}>()
</script>

<template>
  <div class="notification-dropdown" role="menu" aria-label="알림 목록">
    <div class="notification-dropdown__head">알림</div>
    <div v-if="!list.length" class="notification-dropdown__empty">
      새 알림이 없습니다
    </div>
    <ul v-else class="notification-dropdown__list">
      <li
        v-for="(n, i) in list"
        :key="n.id ?? i"
        class="notification-dropdown__item"
        role="menuitem"
      >
        <p class="notification-dropdown__title">{{ n.title ?? n.message }}</p>
        <p v-if="n.body" class="notification-dropdown__body">{{ n.body }}</p>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.notification-dropdown {
  width: 288px;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  font-family: var(--font-sans);
  color: var(--text-primary);
}
.notification-dropdown__head {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}
.notification-dropdown__empty {
  padding: var(--space-6) var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}
.notification-dropdown__list {
  list-style: none; padding: 0; margin: 0;
  max-height: 15rem;
  overflow-y: auto;
}
.notification-dropdown__item {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-sm);
}
.notification-dropdown__item:last-child { border-bottom: 0; }
.notification-dropdown__title {
  margin: 0;
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.notification-dropdown__body {
  margin: 2px 0 0;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}
</style>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const currentPath = computed(() => route.path)

const navItems = [
  { path: '/',          icon: '🏠', label: '홈' },
  { path: '/recommend', icon: '⭐', label: '추천/신호' },
  { path: '/screener',  icon: '🔍', label: '스크리너' },
  { path: '/compare',   icon: '⚖️', label: '비교' },
]
</script>

<template>
  <div id="app">
    <RouterView />

    <!-- GNB -->
    <nav class="gnb">
      <ul class="gnb__list">
        <li v-for="item in navItems" :key="item.path">
          <RouterLink :to="item.path" class="gnb__item"
            :class="{ active: currentPath === item.path }">
            <span class="gnb__icon">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </RouterLink>
        </li>
      </ul>
    </nav>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const offline = ref(!navigator.onLine)

function onOnline()  { offline.value = false }
function onOffline() { offline.value = true }

onMounted(() => {
  window.addEventListener('online',  onOnline)
  window.addEventListener('offline', onOffline)
})
onBeforeUnmount(() => {
  window.removeEventListener('online',  onOnline)
  window.removeEventListener('offline', onOffline)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="banner">
      <div
        v-if="offline"
        class="fixed top-0 left-0 right-0 z-[200] flex items-center justify-center gap-2 py-2 text-sm text-white font-medium"
        style="background: #DC2626"
      >
        <span>📡</span>
        <span>오프라인 상태입니다. 마지막으로 조회한 데이터를 표시합니다.</span>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.banner-enter-active, .banner-leave-active { transition: transform 0.3s, opacity 0.3s; }
.banner-enter-from, .banner-leave-to { transform: translateY(-100%); opacity: 0; }
</style>

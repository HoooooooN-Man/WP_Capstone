import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(localStorage.getItem('theme') === 'dark')

  // html 클래스 동기화
  function applyTheme(dark) {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }

  function toggleDark() {
    isDark.value = !isDark.value
  }

  watch(isDark, applyTheme, { immediate: true })

  return { isDark, toggleDark }
})

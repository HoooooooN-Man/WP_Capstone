import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token    = ref(null)
  const nickname = ref(null)
  const userId   = ref(null)

  const isLoggedIn = computed(() => !!token.value)

  function login(newToken, newNickname, newUserId) {
    token.value    = newToken
    nickname.value = newNickname
    userId.value   = newUserId
    localStorage.setItem('session_token', newToken     ?? '')
    localStorage.setItem('nickname',      newNickname  ?? '')
    localStorage.setItem('userId',        newUserId    ?? '')
  }

  function logout() {
    token.value    = null
    nickname.value = null
    userId.value   = null
    localStorage.removeItem('session_token')
    localStorage.removeItem('nickname')
    localStorage.removeItem('userId')
  }

  function initFromStorage() {
    const storedToken = localStorage.getItem('session_token')
    if (storedToken) {
      token.value    = storedToken
      nickname.value = localStorage.getItem('nickname')
      userId.value   = localStorage.getItem('userId')
    }
  }

  return { token, nickname, userId, isLoggedIn, login, logout, initFromStorage }
})

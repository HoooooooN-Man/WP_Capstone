import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_AUTH ?? 'http://localhost:8000'

const dbapi = axios.create({
  baseURL: BASE,
})

dbapi.interceptors.request.use((config) => {
  const token = localStorage.getItem('session_token')
  if (token) {
    config.headers['session-token'] = token
  }
  return config
})

dbapi.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('session_token')
      // App.vue가 authStore.isLoggedIn을 감시하므로 자동으로 AuthWallet 표시
      window.dispatchEvent(new CustomEvent('auth:logout'))
    }
    return Promise.reject(err)
  }
)

export default dbapi

import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
const instance = axios.create({
  baseURL: `${BASE}/api/v1`,
  timeout: 30000,
})

// Request interceptor: attach session token
instance.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers['session-token'] = auth.token
  }
  return config
})

// Response interceptor: handle 401
instance.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
    }
    return Promise.reject(err)
  }
)

export default instance

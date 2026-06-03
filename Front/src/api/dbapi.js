import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_AUTH ?? 'http://localhost:8000'

const dbapi = axios.create({
  baseURL: BASE,
})

// 요청 인터셉터: 세션 토큰 자동 포함
dbapi.interceptors.request.use((config) => {
  const token = localStorage.getItem('session_token')
  if (token) {
    config.headers['session-token'] = token
  }
  return config
})

// 응답 인터셉터: 401 자동 로그아웃
dbapi.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('session_token')
      // 이미 /login이면 루프 방지
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default dbapi
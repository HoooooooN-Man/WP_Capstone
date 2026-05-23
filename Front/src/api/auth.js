import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_AUTH ?? 'http://localhost:8000'
const authApi = axios.create({
  baseURL: BASE,
  timeout: 10000,
})

// ── 임시 테스트 계정 (실제 auth 서버 연결 후 아래 블록 전체 삭제) ──────────────
const MOCK_USER = { id: 'test1234@gmail.com', email: 'test1234@gmail.com', password: 'test1234', nickname: 'tester' }
function mockLogin(data) {
  if (data.email === MOCK_USER.email && data.password === MOCK_USER.password) {
    return Promise.resolve({ data: { session_token: 'mock-token-test1234', nickname: MOCK_USER.nickname, user_id: MOCK_USER.id } })
  }
  return Promise.reject({ response: { status: 401 } })
}
// ─────────────────────────────────────────────────────────────────────────────

export default {
  checkEmail:            (email)        => authApi.post('/auth/check-email', null, { params: { email } }),
  verifyCode:            (data)         => authApi.post('/auth/verify-code', data),
  register:              (data)         => authApi.post('/auth/register', data),
  login:                 (data)         => mockLogin(data), // ← 실제 서버 연결 시: authApi.post('/auth/login', data)
  resetPassword:         (data, token)  => authApi.post('/auth/reset-password', data, { headers: { 'session-token': token } }),
  resetPasswordViaEmail: (data)         => authApi.post('/auth/reset-password-via-email', data),
}

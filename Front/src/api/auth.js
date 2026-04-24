import axios from 'axios'

const authApi = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
})

export default {
  checkEmail:           (email)                       => authApi.post('/auth/check-email', null, { params: { email } }),
  verifyCode:           (data)                        => authApi.post('/auth/verify-code', data),
  register:             (data)                        => authApi.post('/auth/register', data),
  login:                (data)                        => authApi.post('/auth/login', data),
  resetPassword:        (data, token)                 => authApi.post('/auth/reset-password', data, { headers: { 'session-token': token } }),
  resetPasswordViaEmail:(data)                        => authApi.post('/auth/reset-password-via-email', data),
}

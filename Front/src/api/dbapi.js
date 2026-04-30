import axios from 'axios';

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const dbapi = axios.create({
  baseURL: BASE,
});

// 요청 인터셉터: 세션 토큰이 있으면 헤더에 자동 포함
dbapi.interceptors.request.use((config) => {
  const token = localStorage.getItem('session_token');
  if (token) {
    config.headers['session-token'] = token;
  }
  return config;
});

export default dbapi;
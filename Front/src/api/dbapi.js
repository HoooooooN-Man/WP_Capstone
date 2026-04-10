import axios from 'axios';

const dbapi = axios.create({
  baseURL: 'http://100.67.18.188:8000', // FastAPI 서버 주소
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
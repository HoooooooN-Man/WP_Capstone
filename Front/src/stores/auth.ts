import { defineStore } from 'pinia';
import axios from 'axios';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as { nickname: string } | null,
    sessionToken: localStorage.getItem('session_token') || null,
    isLoggedIn: !!localStorage.getItem('session_token'),
  }),

  actions: {
    async login(loginData: any) {
      try {
        // 실제 백엔드 주소에 맞게 수정 (예: http://100.67.18.188:8000)
        const response = await axios.post('/auth/login', loginData);
        const { session_token, nickname } = response.data;

        this.sessionToken = session_token;
        this.user = { nickname };
        this.isLoggedIn = true;

        localStorage.setItem('session_token', session_token);
        localStorage.setItem('nickname', nickname); // 새로고침 대비 닉네임 저장
        
        axios.defaults.headers.common['session-token'] = session_token;
      } catch (error) {
        console.error('Login failed:', error);
        throw error;
      }
    },

    logout() {
      this.user = null;
      this.sessionToken = null;
      this.isLoggedIn = false;
      localStorage.removeItem('session_token');
      localStorage.removeItem('nickname');
      delete axios.defaults.headers.common['session-token'];
    },

    // 앱 시작 시 호출하여 상태 복구
    initializeAuth() {
      const token = localStorage.getItem('session_token');
      const nickname = localStorage.getItem('nickname');
      if (token && nickname) {
        this.sessionToken = token;
        this.user = { nickname };
        this.isLoggedIn = true;
        axios.defaults.headers.common['session-token'] = token;
      }
    }
  }
});
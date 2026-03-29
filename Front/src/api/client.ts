/**
 * API 클라이언트 - 백엔드 통신 관리
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

// 세션 토큰 저장 (localStorage)
export const getSessionToken = (): string | null => {
  return localStorage.getItem('session_token');
};

export const setSessionToken = (token: string): void => {
  localStorage.setItem('session_token', token);
};

export const clearSessionToken = (): void => {
  localStorage.removeItem('session_token');
};

// API 요청 헬퍼
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (options.headers) {
    const headersFromOptions = new Headers(options.headers);
    headersFromOptions.forEach((value, key) => {
      headers[key] = value;
    });
  }

  // 인증이 필요한 요청이면 토큰 추가
  const token = getSessionToken();
  if (token && !endpoint.includes('/auth/')) {
    headers['session-token'] = token;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// ─── 인증 API ───────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  session_token: string;
  nickname: string;
}

export const authAPI = {
  // 이메일 중복 검사 + 인증코드 발송
  checkEmail: (email: string) =>
    apiCall(`/auth/check-email?email=${encodeURIComponent(email)}`, { method: 'POST' }),

  // 인증 코드 확인
  verifyCode: (email: string, code: string) =>
    apiCall('/auth/verify-code', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    }),

  // 회원가입
  register: (email: string, password: string, nickname: string) =>
    apiCall('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, nickname }),
    }),

  // 로그인
  login: (email: string, password: string): Promise<LoginResponse> =>
    apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  // 로그아웃 (토큰 제거)
  logout: () => {
    clearSessionToken();
  },
};

// ─── 주식 API ───────────────────────────────────────────────────────

export const stocksAPI = {
  // 모델 버전 목록
  getVersions: () => apiCall('/api/v1/stocks/versions'),

  // 날짜 목록
  getDates: (modelVersion: string = 'latest') =>
    apiCall(`/api/v1/stocks/dates?model_version=${modelVersion}`),

  // 특정 날짜 추천 종목
  getStockScores: (date: string, modelVersion: string = 'latest') =>
    apiCall(`/api/v1/stocks/${date}?model_version=${modelVersion}`),

  // 특정 종목 이력
  getStockHistory: (ticker: string, modelVersion: string = 'latest') =>
    apiCall(`/api/v1/stocks/history/${ticker}?model_version=${modelVersion}`),

  // 섹터 정보
  getSectorInfo: (modelVersion: string = 'latest') =>
    apiCall(`/api/v1/stocks/sectors?model_version=${modelVersion}`),
};

// ─── 포트폴리오 API ──────────────────────────────────────────────────

export const portfolioAPI = {
  // 백테스트 요약
  getBacktestSummary: () => apiCall('/portfolio/backtest/summary'),

  // 월별 수익률
  getBacktestMonthly: () => apiCall('/portfolio/backtest/monthly'),
};

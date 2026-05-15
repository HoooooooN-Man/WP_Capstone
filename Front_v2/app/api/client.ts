/**
 * api/client.ts
 *
 * 두 백엔드 (8001 ML / 8000 Auth) 공통 fetch 클라이언트.
 * vite.config.ts 의 proxy 가 /api/v1 → 8001, /auth /users → 8000 으로 라우팅.
 *
 * 인증 토큰 자동 부착 (PRD §6 — Backend_Spec):
 *   - 8000 서버는 `session-token` 헤더로 인증
 *   - localStorage 'session-token' 에 저장됨
 */

import { useSyncExternalStore } from 'react';

const SESSION_KEY = 'session-token';

// ── 세션 토큰 외부 스토어 ────────────────────────────────────────────────
// localStorage 는 React 밖의 상태이므로 useSyncExternalStore 로 구독한다.
// setSessionToken 호출 시 모든 구독 컴포넌트가 즉시 리렌더 → 헤더/레일이
// 로그인·로그아웃에 반응형으로 갱신된다.
const sessionListeners = new Set<() => void>();

export function getSessionToken(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

export function setSessionToken(token: string | null) {
  try {
    if (token) localStorage.setItem(SESSION_KEY, token);
    else localStorage.removeItem(SESSION_KEY);
  } catch { /* ignore */ }
  sessionListeners.forEach((l) => l());
}

function subscribeSession(cb: () => void): () => void {
  sessionListeners.add(cb);
  // 다른 탭에서의 로그인/로그아웃도 반영
  const onStorage = (e: StorageEvent) => {
    if (e.key === SESSION_KEY) cb();
  };
  window.addEventListener('storage', onStorage);
  return () => {
    sessionListeners.delete(cb);
    window.removeEventListener('storage', onStorage);
  };
}

/** 세션 토큰을 반응형으로 구독 — 로그인 상태 분기는 이 훅을 쓴다 */
export function useSession(): { token: string | null; isLoggedIn: boolean } {
  const token = useSyncExternalStore(subscribeSession, getSessionToken, () => null);
  return { token, isLoggedIn: !!token };
}

export interface ApiError extends Error {
  status: number;
  code?: string;
  request_id?: string;
}

/** GET 쿼리스트링/POST URL params 로 직렬화 가능한 원시 값들 */
type ParamValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, ParamValue>;

async function request<T>(
  path: string,
  options: RequestInit & { params?: QueryParams } = {},
): Promise<T> {
  const { params, headers, ...init } = options;

  // 쿼리스트링 조립
  let url = path;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        qs.append(k, String(v));
      }
    });
    const qsStr = qs.toString();
    if (qsStr) url += (path.includes('?') ? '&' : '?') + qsStr;
  }

  // 인증 헤더 자동 부착 (auth 라우트가 아닐 때)
  const token = getSessionToken();
  const finalHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && !path.startsWith('/auth/') ? { 'session-token': token } : {}),
    ...headers,
  };

  const res = await fetch(url, { ...init, headers: finalHeaders });

  if (!res.ok) {
    type ErrPayload = { message?: string; code?: string; request_id?: string };
    let payload: ErrPayload | null = null;
    try { payload = (await res.json()) as ErrPayload; } catch { /* not JSON */ }
    const err: ApiError = Object.assign(new Error(payload?.message ?? `HTTP ${res.status}`), {
      status: res.status,
      code: payload?.code,
      request_id: payload?.request_id,
    });
    throw err;
  }

  // 204 No Content
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

export const api = {
  get:   <T>(path: string, params?: QueryParams) =>
    request<T>(path, { method: 'GET', params }),
  post:  <T>(path: string, body?: unknown, params?: QueryParams) =>
    request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined, params }),
  put:   <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete:<T>(path: string) =>
    request<T>(path, { method: 'DELETE' }),
};

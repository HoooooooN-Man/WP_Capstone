/**
 * api/client.ts
 *
 * 두 백엔드 (8001 ML / 8000 Auth) 공통 fetch 클라이언트.
 * vite.config.ts 의 proxy 가 /api/v1 → 8001, /auth /users → 8000 으로 라우팅.
 *
 * 인증 (H#27 후 dual-mode):
 *   - **신규(권장)**: 8000 이 `wp_session` HttpOnly 쿠키를 set. 브라우저가 자동 첨부.
 *     credentials: 'include' + dev proxy 가 같은 origin 이므로 쿠키 그대로 전달.
 *     세션 상태는 `/auth/session` 으로 확인 (토큰 값은 JS 에서 읽을 수 없음).
 *   - **legacy**: localStorage 'session-token' 헤더 — 쿠키 미지원 환경 호환용.
 *     점진 deprecate. 둘 다 보내면 백엔드가 cookie 우선.
 */

import { useEffect, useSyncExternalStore } from 'react';

const SESSION_KEY = 'session-token';

// ── 세션 상태 외부 스토어 ─────────────────────────────────────────────────
// 쿠키 기반 인증은 JS 에서 토큰을 직접 못 읽으므로 nickname 등 식별 정보를 별도 관리.
// localStorage 의 'session-token' (legacy) 또는 'wp_session_nick' (cookie 모드 marker)
// 중 하나라도 있으면 isLoggedIn=true.
const NICK_KEY = 'wp_session_nick';
const sessionListeners = new Set<() => void>();

interface SessionSnapshot {
  /** legacy 헤더 모드의 토큰. cookie 모드에서는 항상 null. */
  token: string | null;
  /** 로그인 사용자 nickname (cookie 모드에서는 /auth/session 결과로 hydrate). */
  nickname: string | null;
  /** true = 둘 중 하나라도 로그인. */
  isLoggedIn: boolean;
}

function readSnapshot(): SessionSnapshot {
  try {
    const token = localStorage.getItem(SESSION_KEY);
    const nickname = localStorage.getItem(NICK_KEY);
    return { token, nickname, isLoggedIn: !!(token || nickname) };
  } catch {
    return { token: null, nickname: null, isLoggedIn: false };
  }
}

// 안정된 reference — useSyncExternalStore 가 같은 값이면 리렌더 안 함.
let _cachedSnap: SessionSnapshot = readSnapshot();
function refreshSnapshot(): void {
  const next = readSnapshot();
  // shallow equal check
  if (
    next.token === _cachedSnap.token &&
    next.nickname === _cachedSnap.nickname &&
    next.isLoggedIn === _cachedSnap.isLoggedIn
  ) return;
  _cachedSnap = next;
  sessionListeners.forEach((l) => l());
}

export function getSessionToken(): string | null {
  return _cachedSnap.token;
}

export function getSessionNickname(): string | null {
  return _cachedSnap.nickname;
}

/** Legacy 헤더 모드 — 로그인 응답의 session_token 을 저장. cookie 모드면 null 호출. */
export function setSessionToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(SESSION_KEY, token);
    else localStorage.removeItem(SESSION_KEY);
  } catch { /* ignore */ }
  refreshSnapshot();
}

/** 로그인 상태 marker. cookie 모드에서는 token 없이 nickname 만 set. */
export function setSessionNickname(nickname: string | null): void {
  try {
    if (nickname) localStorage.setItem(NICK_KEY, nickname);
    else localStorage.removeItem(NICK_KEY);
  } catch { /* ignore */ }
  refreshSnapshot();
}

/** 클라이언트 측 로그아웃 — 둘 다 정리. 서버 `/auth/logout` 은 별도 호출. */
export function clearSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(NICK_KEY);
  } catch { /* ignore */ }
  refreshSnapshot();
}

function subscribeSession(cb: () => void): () => void {
  sessionListeners.add(cb);
  const onStorage = (e: StorageEvent) => {
    if (e.key === SESSION_KEY || e.key === NICK_KEY) refreshSnapshot();
  };
  window.addEventListener('storage', onStorage);
  return () => {
    sessionListeners.delete(cb);
    window.removeEventListener('storage', onStorage);
  };
}

/** 세션 상태를 반응형으로 구독 — UI 분기는 이 훅을 쓴다. */
export function useSession(): SessionSnapshot {
  return useSyncExternalStore(
    subscribeSession,
    () => _cachedSnap,
    () => _cachedSnap,
  );
}

/** 앱 부팅 시 1회 호출 — 쿠키 모드에서 nickname hydrate. */
export function useSessionBootstrap(): void {
  useEffect(() => {
    // 이미 nickname 가 있으면 skip — 토큰 만료라면 401 시 자동 정리됨.
    if (_cachedSnap.nickname || _cachedSnap.token) return;
    fetch('/auth/session', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.nickname) setSessionNickname(d.nickname); })
      .catch(() => { /* unauthenticated — 무시 */ });
  }, []);
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

  // legacy 헤더 모드: localStorage 토큰이 있으면 첨부.
  // cookie 모드: credentials 'include' 가 브라우저에 위임 — JS 가 토큰을 못 읽음.
  const token = getSessionToken();
  const finalHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && !path.startsWith('/auth/') ? { 'session-token': token } : {}),
    ...headers,
  };

  const res = await fetch(url, {
    ...init,
    headers: finalHeaders,
    // H#27: 모든 요청에 쿠키 포함 — 같은 origin 이라 dev/prod 둘 다 정상.
    credentials: 'include',
  });

  if (!res.ok) {
    type ErrPayload = { message?: string; code?: string; request_id?: string };
    let payload: ErrPayload | null = null;
    try { payload = (await res.json()) as ErrPayload; } catch { /* not JSON */ }
    // 401 자동 정리 — 만료/위변조 시 클라이언트 상태도 비움.
    if (res.status === 401 && !path.startsWith('/auth/')) {
      clearSession();
    }
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

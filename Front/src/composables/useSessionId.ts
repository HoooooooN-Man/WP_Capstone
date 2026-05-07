/**
 * useSessionId.ts — 비로그인 사용자의 안정적 식별자.
 *
 * 정책 (W1B 결정):
 *   - localStorage 에 64자 이내 ID 한 개 persist.
 *   - 비로그인 events 적재(`/events/impressions` 등)에 `session_id` 로 전달.
 *   - 로그인 후에도 ID 는 유지 (사용자 단위 분석 외 device 단위 분석을 위해).
 *
 * 새 ID 는 페이지 첫 진입 시 한 번만 생성. PWA·다중 탭에서도 같은 값.
 */
const STORAGE_KEY = 'event_session_id_v1'

function _generate(): string {
  // 짧은 32-hex (UUID4 hex 절반 길이로 충분, 64자 제약 안전).
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return 'anon_' + crypto.randomUUID().replace(/-/g, '').slice(0, 32)
  }
  // fallback — 일부 구형 브라우저.
  return 'anon_' + Math.random().toString(16).slice(2) + Date.now().toString(16)
}

export function useSessionId(): string {
  try {
    let sid = localStorage.getItem(STORAGE_KEY)
    if (!sid) {
      sid = _generate()
      localStorage.setItem(STORAGE_KEY, sid)
    }
    return sid
  } catch {
    // localStorage 미가용 (privacy mode) — 메모리 단명 ID.
    return _generate()
  }
}

/** 테스트·디버그용 — 강제 재생성. */
export function resetSessionId(): string {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
  return useSessionId()
}

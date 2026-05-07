/**
 * useCohort.ts — W2 cohort 선택 영속화·동기화.
 *
 * 정책:
 *   - 비로그인: localStorage (`cohort_v1`) 단독.
 *   - 로그인: 서버 (`/users/me/cohort`) 가 source of truth, localStorage 는 캐시.
 *   - 로그인 직후 1회: localStorage 잔류분이 있으면 서버로 마이그레이션 (Watchlist 패턴).
 *   - 미선택 사용자도 정상 — null = balanced 와 동치.
 */
import { ref } from 'vue'
import dbapi from '@/api/dbapi'

const STORAGE_KEY = 'cohort_v1'
const VALID = new Set(['conservative', 'balanced', 'growth', 'dividend', 'value'])

const cohort = ref<string | null>(_loadLocal())

function _loadLocal(): string | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const c = raw.toLowerCase()
    return VALID.has(c) ? c : null
  } catch {
    return null
  }
}

function _saveLocal(c: string | null): void {
  try {
    if (c === null) localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, c)
  } catch (e) {
    console.error('[cohort] localStorage write failed', e)
  }
}

export function useCohort() {
  /** 현재 cohort. 컴포넌트가 ref 로 사용 가능. */
  const value = cohort

  /** 로컬·서버 동시 갱신. 로그인 안 된 경우 서버 호출 skip. */
  async function setCohort(next: string | null, { authenticated = false } = {}): Promise<void> {
    const norm = next ? next.toLowerCase() : null
    if (norm !== null && !VALID.has(norm)) {
      throw new Error(`invalid cohort: ${next}`)
    }
    cohort.value = norm
    _saveLocal(norm)

    if (authenticated) {
      try {
        await dbapi.put('/users/me/cohort', { cohort: norm })
      } catch (e) {
        console.error('[cohort] server PUT failed; localStorage 만 유지', e)
      }
    }
  }

  /** 로그인 직후 호출 — 서버에 cohort 가 없으면 로컬 잔류분 마이그레이션. */
  async function syncOnLogin(): Promise<void> {
    try {
      const r = await dbapi.get<{ cohort: string | null }>('/users/me/cohort')
      const server = r.data?.cohort ?? null
      if (server) {
        // 서버 우선.
        cohort.value = server
        _saveLocal(server)
      } else if (cohort.value) {
        // 서버는 비어있고 로컬에 있음 → 서버로 이관.
        await dbapi.put('/users/me/cohort', { cohort: cohort.value })
      }
    } catch (e) {
      console.error('[cohort] syncOnLogin failed', e)
    }
  }

  return { value, setCohort, syncOnLogin }
}

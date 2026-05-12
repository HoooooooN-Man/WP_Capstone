// UX W5 — 사용자 프로필 composable.
// 결정: 권고 수용 — auth.user 기반 fallback (별 endpoint 호출 안 함).
// /users/me endpoint 가 없으면 auth store 의 user 정보만 사용.

import { computed } from 'vue'

export interface UserProfile {
  name:        string
  email:       string
  joinedAt:    string | null    // ISO 또는 "YYYY-MM" 등
  isAnonymous: boolean
}

// 이니셜 추출 (avatar 텍스트용). 권고: 이니셜 텍스트.
export function deriveInitials(name: string | null | undefined): string {
  if (!name) return '?'
  const trimmed = String(name).trim()
  if (!trimmed) return '?'
  // 한글: 첫 1자. 영문: 단어 첫 자 최대 2.
  if (/^[ㄱ-힝]/.test(trimmed)) return trimmed.charAt(0)
  const parts = trimmed.split(/\s+/).filter(Boolean)
  return parts.map(p => p.charAt(0).toUpperCase()).slice(0, 2).join('')
}

// 가입일 format (YYYY-MM-DD → "YYYY.MM" 단순).
export function formatJoinedAt(iso: string | null | undefined): string {
  if (!iso) return '-'
  const m = /^(\d{4})-(\d{2})/.exec(String(iso))
  if (!m) return String(iso)
  return `${m[1]}.${m[2]}`
}

// auth store user object → UserProfile graceful 변환.
export function mapAuthUser(user: any | null | undefined): UserProfile {
  if (!user) {
    return { name: '게스트', email: '', joinedAt: null, isAnonymous: true }
  }
  return {
    name:        String(user.name ?? user.username ?? user.nickname ?? '사용자'),
    email:       String(user.email ?? ''),
    joinedAt:    user.joined_at ?? user.created_at ?? null,
    isAnonymous: false,
  }
}

// 본 composable 의 정체 — 별 fetch 안 함. auth store 의 user 반응형 매핑.
export function useUserProfile(authStore: { user?: any }) {
  const profile = computed<UserProfile>(() => mapAuthUser(authStore.user))
  return { profile }
}

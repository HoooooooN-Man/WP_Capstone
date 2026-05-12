import { describe, it, expect } from 'vitest'
import { reactive } from 'vue'
import {
  deriveInitials, formatJoinedAt, mapAuthUser, useUserProfile,
} from '@/composables/useUserProfile'

describe('deriveInitials', () => {
  it('한글 → 첫 1자', () => {
    expect(deriveInitials('김ㅇㅇ')).toBe('김')
    expect(deriveInitials('박지영')).toBe('박')
  })

  it('영문 → 단어 첫 자 최대 2', () => {
    expect(deriveInitials('John')).toBe('J')
    expect(deriveInitials('John Doe')).toBe('JD')
    expect(deriveInitials('john doe smith')).toBe('JD')
  })

  it('빈 입력 → "?"', () => {
    expect(deriveInitials('')).toBe('?')
    expect(deriveInitials(null)).toBe('?')
    expect(deriveInitials(undefined)).toBe('?')
    expect(deriveInitials('   ')).toBe('?')
  })

  it('대소문자 정규화', () => {
    expect(deriveInitials('john doe')).toBe('JD')
  })
})

describe('formatJoinedAt', () => {
  it('YYYY-MM-DD → YYYY.MM', () => {
    expect(formatJoinedAt('2026-03-15')).toBe('2026.03')
    expect(formatJoinedAt('2026-03-15T10:00:00Z')).toBe('2026.03')
  })

  it('null/undefined → "-"', () => {
    expect(formatJoinedAt(null)).toBe('-')
    expect(formatJoinedAt(undefined)).toBe('-')
  })

  it('잘못된 형식 → 원본 그대로', () => {
    expect(formatJoinedAt('invalid')).toBe('invalid')
  })
})

describe('mapAuthUser', () => {
  it('user 객체 → UserProfile', () => {
    const p = mapAuthUser({
      name: '김ㅇㅇ', email: 'kim@example.com', joined_at: '2026-03-15',
    })
    expect(p.name).toBe('김ㅇㅇ')
    expect(p.email).toBe('kim@example.com')
    expect(p.joinedAt).toBe('2026-03-15')
    expect(p.isAnonymous).toBe(false)
  })

  it('null user → 게스트', () => {
    const p = mapAuthUser(null)
    expect(p.name).toBe('게스트')
    expect(p.email).toBe('')
    expect(p.joinedAt).toBe(null)
    expect(p.isAnonymous).toBe(true)
  })

  it('name 부재 시 username·nickname fallback', () => {
    expect(mapAuthUser({ username: 'jdoe' }).name).toBe('jdoe')
    expect(mapAuthUser({ nickname: 'JD' }).name).toBe('JD')
    expect(mapAuthUser({}).name).toBe('사용자')
  })

  it('created_at fallback', () => {
    const p = mapAuthUser({ name: 'X', created_at: '2026-01-01' })
    expect(p.joinedAt).toBe('2026-01-01')
  })
})

describe('useUserProfile composable', () => {
  it('auth store user 반응형 매핑', () => {
    const store = reactive({ user: { name: '김ㅇㅇ', email: 'k@x.com' } })
    const { profile } = useUserProfile(store)
    expect(profile.value.name).toBe('김ㅇㅇ')

    // store 변경 시 반응형 갱신
    store.user = { name: 'New', email: 'n@x.com' } as any
    expect(profile.value.name).toBe('New')
  })

  it('user null → 게스트', () => {
    const store = reactive({ user: null as any })
    const { profile } = useUserProfile(store)
    expect(profile.value.isAnonymous).toBe(true)
  })
})

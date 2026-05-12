import { describe, it, expect } from 'vitest'
import {
  COHORT_LABEL, DIVERSIFY_LABEL, formatAsOfDate,
} from '@/composables/useRecommendations'

describe('useRecommendations — 유틸·매핑', () => {
  describe('COHORT_LABEL', () => {
    it('5 코호트 한국어 매핑', () => {
      expect(COHORT_LABEL.balanced).toBe('균형')
      expect(COHORT_LABEL.growth).toBe('성장')
      expect(COHORT_LABEL.dividend).toBe('배당')
      expect(COHORT_LABEL.short_term).toBe('단타')
      expect(COHORT_LABEL.beginner).toBe('입문')
    })
  })

  describe('DIVERSIFY_LABEL', () => {
    it('4 모드 한국어 매핑', () => {
      expect(DIVERSIFY_LABEL.none).toBe('기본')
      expect(DIVERSIFY_LABEL.correlation).toBe('상관')
      expect(DIVERSIFY_LABEL.sector).toBe('섹터')
      expect(DIVERSIFY_LABEL.embedding).toBe('임베딩')
    })
  })

  describe('formatAsOfDate', () => {
    it('YYYY-MM-DD → "M월 D일 기준"', () => {
      expect(formatAsOfDate('2026-04-29')).toBe('4월 29일 기준')
      expect(formatAsOfDate('2026-01-02')).toBe('1월 2일 기준')
      expect(formatAsOfDate('2025-12-31')).toBe('12월 31일 기준')
    })

    it('null/undefined → 빈 문자열', () => {
      expect(formatAsOfDate(null)).toBe('')
      expect(formatAsOfDate(undefined)).toBe('')
    })

    it('잘못된 형식 → 원본 그대로 (graceful)', () => {
      expect(formatAsOfDate('invalid')).toBe('invalid')
      expect(formatAsOfDate('2026/04/29')).toBe('2026/04/29')
    })

    it('ISO timestamp 도 날짜만 추출', () => {
      expect(formatAsOfDate('2026-04-29T13:00:00Z')).toBe('4월 29일 기준')
    })
  })
})

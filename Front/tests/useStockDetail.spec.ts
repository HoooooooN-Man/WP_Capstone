import { describe, it, expect } from 'vitest'
import {
  formatPrice, formatChange, changeClass,
  formatFinanceQuarter, pickLatest,
  type FinanceRow,
} from '@/composables/useStockDetail'

describe('useStockDetail — 유틸', () => {
  describe('formatPrice', () => {
    it('한국어 천 단위 구분', () => {
      expect(formatPrice(70500)).toBe('70,500')
      expect(formatPrice(1234567)).toBe('1,234,567')
    })

    it('null/undefined/NaN → "-" graceful', () => {
      expect(formatPrice(null)).toBe('-')
      expect(formatPrice(undefined)).toBe('-')
      expect(formatPrice(NaN)).toBe('-')
      expect(formatPrice(Infinity)).toBe('-')
    })

    it('0 → "0"', () => {
      expect(formatPrice(0)).toBe('0')
    })
  })

  describe('formatChange', () => {
    it('상승 → ▲ + 절대값', () => {
      expect(formatChange(1.25)).toBe('▲ 1.25%')
    })

    it('하락 → ▼ + 절대값', () => {
      expect(formatChange(-2.5)).toBe('▼ 2.50%')
    })

    it('0 → "-"', () => {
      expect(formatChange(0)).toBe('- 0.00%')
    })

    it('null/undefined/Infinity → "-"', () => {
      expect(formatChange(null)).toBe('-')
      expect(formatChange(undefined)).toBe('-')
      expect(formatChange(Infinity)).toBe('-')
    })
  })

  describe('changeClass', () => {
    it('양수 → change--up', () => {
      expect(changeClass(1.5)).toBe('change--up')
    })

    it('음수 → change--down', () => {
      expect(changeClass(-1.5)).toBe('change--down')
    })

    it('0·null·undefined → 빈 문자열', () => {
      expect(changeClass(0)).toBe('')
      expect(changeClass(null)).toBe('')
      expect(changeClass(undefined)).toBe('')
    })
  })

  describe('formatFinanceQuarter', () => {
    it('year·quarter → YYYYQN', () => {
      const r: FinanceRow = { year: 2026, quarter: 1 }
      expect(formatFinanceQuarter(r)).toBe('2026Q1')
    })

    it('Q4', () => {
      expect(formatFinanceQuarter({ year: 2025, quarter: 4 })).toBe('2025Q4')
    })
  })

  describe('pickLatest', () => {
    it('date 기준 최신 row 선택', () => {
      const rows = [
        { date: '2026-04-29', x: 1 },
        { date: '2026-04-30', x: 2 },
        { date: '2026-04-15', x: 3 },
      ]
      expect(pickLatest(rows)?.x).toBe(2)
    })

    it('빈 배열 → undefined', () => {
      expect(pickLatest([])).toBeUndefined()
    })

    it('date 부재 graceful', () => {
      const rows = [{ x: 1 }, { x: 2 }]
      // 둘 다 date 없으면 마지막 (혹은 처음) 반환 — 빈 문자열 동일 정렬
      const r = pickLatest(rows)
      expect(r).toBeDefined()
    })

    it('단일 row → 그대로', () => {
      expect(pickLatest([{ date: '2026-01-01', x: 9 }])?.x).toBe(9)
    })
  })
})

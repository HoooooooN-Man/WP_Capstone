// UX W4 — StockDetailView 의 5 영역 Vue Query composable 집합.
// 결정: 차트+기본정보 즉시, 재무·뉴스·공시 lazy (탭 진입 enabled).
// 공시 endpoint 부재 → empty state placeholder.

import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery } from '@tanstack/vue-query'
// @ts-ignore — 기존 axios.js 캡스톤 잔재
import api from '@/api/axios'

// ── 타입 ────────────────────────────────────────────────────────────────

export interface StockHistoryRow {
  date: string
  ticker: string
  name?: string | null
  sector?: string | null
  close?: number | null
  prob_ensemble?: number | null
  score?: number | null
  tier?: 'A' | 'B' | 'C' | 'D' | null
  rank_in_date?: number | null
  total_in_date?: number | null
  model_version?: string | null
}

export interface ChartCandle {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface FinanceRow {
  year: number
  quarter: number
  per?: number | null
  pbr?: number | null
  roe?: number | null
  debt_ratio?: number | null
  op_margin?: number | null
  rev_growth_yoy?: number | null
  finance_score?: number | null
}

export interface NewsItem {
  news_id: string
  title: string
  source?: string
  published_at?: string
  sentiment_label?: 'positive' | 'neutral' | 'negative' | null
  url?: string
}

export interface DisclosureItem {
  rcept_no: string
  rcept_dt: string
  report_nm: string
  pblntf_ty?: string | null
  pblntf_detail_ty?: string | null
}

// ── 기본정보·score history (즉시) ──────────────────────────────────────────

const FIVE_MIN = 5 * 60 * 1000
const ONE_HOUR = 60 * 60 * 1000

export function useStockBasic(ticker: Ref<string>) {
  return useQuery({
    queryKey: computed(() => ['stock', 'history', ticker.value]) as any,
    queryFn: async (): Promise<StockHistoryRow[]> => {
      const { data } = await api.get(`/api/v1/stocks/${ticker.value}/history`)
      // 응답 형식 — items 또는 list 형태 호환
      return (data.items ?? data.history ?? data ?? []) as StockHistoryRow[]
    },
    enabled: computed(() => !!ticker.value),
    staleTime: FIVE_MIN,
    retry: 1,
  })
}

// ── 차트 (즉시) ────────────────────────────────────────────────────────────

export function useStockChart(ticker: Ref<string>) {
  return useQuery({
    queryKey: computed(() => ['stock', 'chart', ticker.value]) as any,
    queryFn: async (): Promise<ChartCandle[]> => {
      const { data } = await api.get(`/api/v1/chart/${ticker.value}`)
      return (data.items ?? data.candles ?? data ?? []) as ChartCandle[]
    },
    enabled: computed(() => !!ticker.value),
    staleTime: ONE_HOUR,
    retry: 1,
  })
}

// ── 재무 (lazy) ────────────────────────────────────────────────────────────

export function useStockFinance(ticker: Ref<string>, enabled: ComputedRef<boolean>) {
  return useQuery({
    queryKey: computed(() => ['stock', 'finance', ticker.value]) as any,
    queryFn: async (): Promise<FinanceRow[]> => {
      const { data } = await api.get(`/api/v1/finance/${ticker.value}`)
      return (data.items ?? data.history ?? data ?? []) as FinanceRow[]
    },
    enabled: computed(() => !!ticker.value && enabled.value),
    staleTime: ONE_HOUR,
    retry: 1,
  })
}

// ── 뉴스 (lazy) ────────────────────────────────────────────────────────────

export function useStockNews(ticker: Ref<string>, enabled: ComputedRef<boolean>) {
  return useQuery({
    queryKey: computed(() => ['stock', 'news', ticker.value]) as any,
    queryFn: async (): Promise<NewsItem[]> => {
      const { data } = await api.get('/news/feed', {
        params: { ticker: ticker.value, limit: 10 },
      })
      return (data.items ?? []) as NewsItem[]
    },
    enabled: computed(() => !!ticker.value && enabled.value),
    staleTime: FIVE_MIN,
    retry: 1,
  })
}

// ── 공시 (lazy, endpoint 부재 → empty placeholder) ──────────────────────────

export function useStockDisclosures(_ticker: Ref<string>, _enabled: ComputedRef<boolean>) {
  // 백엔드 disclosures router 부재 — 차차차차기 후보로 commit body 박제.
  // 본 composable 은 *항상 empty* 반환, 사용자에게 empty state 노출.
  return {
    data: computed<DisclosureItem[]>(() => []),
    isLoading: computed(() => false),
    isError:   computed(() => false),
    isUnavailable: true as const,
  }
}

// ── 유틸 ──────────────────────────────────────────────────────────────────

export function formatPrice(v: number | null | undefined): string {
  if (v == null || !isFinite(v)) return '-'
  return v.toLocaleString('ko-KR')
}

export function formatChange(v: number | null | undefined): string {
  if (v == null || !isFinite(v)) return '-'
  const sign = v > 0 ? '▲' : v < 0 ? '▼' : '-'
  return `${sign} ${Math.abs(v).toFixed(2)}%`
}

export function changeClass(v: number | null | undefined): string {
  if (v == null || !isFinite(v) || v === 0) return ''
  return v > 0 ? 'change--up' : 'change--down'
}

export function formatFinanceQuarter(row: FinanceRow): string {
  return `${row.year}Q${row.quarter}`
}

export function pickLatest<T extends { date?: string }>(rows: T[]): T | undefined {
  if (!rows.length) return undefined
  const sorted = [...rows].sort((a, b) => (a.date ?? '').localeCompare(b.date ?? ''))
  return sorted[sorted.length - 1]
}

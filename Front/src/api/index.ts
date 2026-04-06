import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8001'

const api = axios.create({
  baseURL: `${BASE}/api/v1`,
  timeout: 15_000,
})

// ── Types ──────────────────────────────────────────────────────────────────

export interface StockScore {
  ticker: string
  name?: string
  sector?: string
  mid_sector?: string
  date: string
  score: number
  tier: string
  model_version: string
  lgbm_prob?: number
  xgb_prob?: number
  cat_prob?: number
}

export interface StockScoreList {
  date: string
  model_version: string
  total: number
  items: StockScore[]
}

export interface StockHistoryItem {
  date: string
  score: number
  tier: string
  model_version: string
}

export interface StockHistory {
  ticker: string
  model_version: string
  total: number
  items: StockHistoryItem[]
}

export interface SectorSummaryItem {
  sector: string
  date: string
  model_version: string
  avg_score: number
  max_score: number
  min_score: number
  a_tier_count: number
  total_count: number
}

export interface SectorSummaryList {
  date: string
  model_version: string
  total: number
  items: SectorSummaryItem[]
}

export interface SearchResult {
  ticker: string
  name?: string
  sector?: string
  mid_sector?: string
  score?: number
  tier?: string
  model_version?: string
  latest_date?: string
}

export interface SearchList {
  query: string
  total: number
  items: SearchResult[]
}

export interface CandleItem {
  date: string
  open?: number
  high?: number
  low?: number
  close?: number
  volume?: number
  amount?: number
  market_cap?: number
  ma5?: number
  ma20?: number
  ma60?: number
  ma120?: number
}

export interface ChartResponse {
  ticker: string
  name?: string
  period: string
  total: number
  items: CandleItem[]
}

export interface FinanceItem {
  year: number
  quarter: number
  base_date?: string
  per?: number
  pbr?: number
  eps?: number
  roe?: number
  debt_ratio?: number
  op_margin?: number
  net_margin?: number
  revenue?: number
  op_profit?: number
  net_profit?: number
  rev_growth_yoy?: number
  finance_score?: number
}

export interface FinanceResponse {
  ticker: string
  name?: string
  total: number
  items: FinanceItem[]
}

export interface FinanceLatest {
  ticker: string
  name?: string
  year?: number
  quarter?: number
  per?: number
  pbr?: number
  roe?: number
  debt_ratio?: number
  op_margin?: number
  revenue?: number
  net_profit?: number
  rev_growth_yoy?: number
  finance_score?: number
}

export interface ScreenerItem {
  ticker: string
  name?: string
  sector?: string
  score?: number
  tier?: string
  latest_date?: string
  per?: number
  pbr?: number
  roe?: number
  debt_ratio?: number
  op_margin?: number
  rev_growth_yoy?: number
  finance_score?: number
  composite_score?: number
}

export interface ScreenerResponse {
  total: number
  items: ScreenerItem[]
}

export interface CompareItem {
  ticker: string
  name?: string
  sector?: string
  latest_score?: number
  latest_tier?: string
  score_history?: StockHistoryItem[]
  finance?: FinanceLatest
}

export interface CompareResponse {
  tickers: string[]
  total: number
  items: CompareItem[]
}

// ── API calls ──────────────────────────────────────────────────────────────

export const stocksApi = {
  recommendations: (params?: Record<string, unknown>) =>
    api.get<StockScoreList>('/stocks/recommendations', { params }),

  history: (ticker: string, params?: Record<string, unknown>) =>
    api.get<StockHistory>(`/stocks/${ticker}/history`, { params }),

  sectorSummary: (params?: Record<string, unknown>) =>
    api.get<SectorSummaryList>('/stocks/sectors/summary', { params }),

  search: (q: string, limit = 20) =>
    api.get<SearchList>('/stocks/search', { params: { q, limit } }),

  versions: () => api.get('/stocks/versions'),
  dates: (model_version = 'latest') =>
    api.get('/stocks/dates', { params: { model_version } }),
}

export const chartApi = {
  get: (ticker: string, period = '1y') =>
    api.get<ChartResponse>(`/chart/${ticker}`, { params: { period } }),
}

export const financeApi = {
  getAll: (ticker: string, limit = 12) =>
    api.get<FinanceResponse>(`/finance/${ticker}`, { params: { limit } }),

  getLatest: (ticker: string) =>
    api.get<FinanceLatest>(`/finance/${ticker}/latest`),
}

export const screenerApi = {
  screen: (params?: Record<string, unknown>) =>
    api.get<ScreenerResponse>('/screener', { params }),
}

export const compareApi = {
  compare: (tickers: string[], period = '1y') =>
    api.get<CompareResponse>('/compare', {
      params: { tickers: tickers.join(','), period },
    }),
}

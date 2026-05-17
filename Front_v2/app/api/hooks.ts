/**
 * api/hooks.ts
 *
 * TanStack Query 래퍼 — 백엔드 엔드포인트별 hook.
 * 응답 타입은 PRD §10 mock + 실 백엔드 스키마에 맞춰 정의.
 * 변환 비용을 줄이기 위해 mutation 결과는 unknown(읽지 않음 가정).
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, clearSession, setSessionNickname, setSessionToken } from './client';

// ── 응답 타입 정의 ─────────────────────────────────────────────────────────

export interface StockItem {
  ticker: string;
  name: string;
  sector?: string;
  close: number;
  score: number;
  tier: 'A' | 'B' | 'C' | 'D';
  signal_label: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  signal_label_ko?: string;
  star_rating?: number;
  percentile_in_sector?: number;
  sector_rank?: number;
  sector_total?: number;
  cumulative_return_pct?: number;
  first_recommended_date?: string;
  days_since_rec?: number;
  headline?: string;
  market_cap_label?: string;
  change_pct?: number;
  // B1: cohort 가중치용 finance 지표 (recommendations 응답에 LEFT JOIN 부착).
  per?: number;
  pbr?: number;
  dividend_yield?: number;
  roe?: number;
  debt_ratio?: number;
  op_margin?: number;
  net_margin?: number;
  rev_growth_yoy?: number;
}

export interface MarketRegime {
  date: string;
  tier_a_ratio: number;
  daily_change: number | null;
  status: 'panic' | 'pessimism' | 'neutral' | 'optimism' | 'greed';
  status_ko: string;
  weather: string;
  mood: string;
  market_score: number;
  score_range: string;
  message: string;
}

export interface RadarGroups {
  growth?: number;
  profitability?: number;
  safety?: number;
  /** 백엔드 v9+ 표준 필드 */
  moat?: number;
  /** v8 이하 별칭 — 일부 페이지가 fallback 으로 참조 */
  monopoly?: number;
  cashflow?: number;
}
export interface RadarResponse {
  groups?: RadarGroups;
  sector_average?: RadarGroups;
}

export interface FairValueInputs {
  eps?: number;
  bps?: number;
  sector_per?: number;
  sector_pbr?: number;
  self_per_med?: number;
  self_pbr_med?: number;
}
export interface FairValueResponse {
  current_price?: number;
  fair_value?: number;
  deviation_pct: number;
  band_ko?: string;
  inputs?: FairValueInputs;
}

export interface DividendScores {
  yield_score?: number;
  consecutive_score?: number;
  growth_score?: number;
  payout_score?: number;
  /** B35: rev_growth_yoy 기반 매출성장 점수 (실제 EPS 데이터 부재로 매출 proxy). */
  rev_growth_score?: number;
  /** @deprecated B35 — rev_growth_score 와 동일값. 하위호환 alias. */
  eps_growth_score?: number;
}
export interface DividendResponse {
  dividend_score?: number;
  yield_pct?: number;
  dps?: number;
  years_paid?: number;
  dps_growth_yoy?: number | null;
  payout_pct?: number | null;
  scores?: DividendScores;
  investment_points?: string[];
}

export interface FinancialItem {
  year: number;
  quarter: number;
  revenue?: number | null;
  op_profit?: number | null;
  net_profit?: number | null;
  per?: number | null;
  pbr?: number | null;
  dividend_yield?: number | null;
  market_cap?: number | null;
}
export interface FinancialsResponse {
  items: FinancialItem[];
}

export interface HistoryItem {
  date: string;
  close?: number | null;
  score?: number | null;
  high?: number | null;
  low?: number | null;
  volume?: number | null;
  foreign_ratio?: number | null;
  shares_outstanding?: number | null;
  market_cap?: number | null;
  signal_label?: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
  tier?: 'A' | 'B' | 'C' | 'D';
  name?: string;
  sector?: string;
}
export interface HistoryResponse {
  items: HistoryItem[];
}

export interface OutcomeResponse {
  cumulative_return_pct?: number;
}

export interface NewsItem {
  // 백엔드 news_normalized.news_id 는 해시 문자열(예: "a1b2…") — number 가 아님.
  // (이전 타입은 number 였는데 런타임에 string 이 들어와 키/라우팅이 불일치했다.)
  id: string | number;
  news_id?: string | number;
  title?: string;
  summary?: string;
  content?: string;
  source?: string;
  company_name?: string;
  published_at?: string;
  image_url?: string | null;
  sentiment_label?: 'positive' | 'negative' | 'neutral';
  related_tickers?: string[];
}
export interface NewsFeedResponse {
  items: NewsItem[];
}

export interface NoteItem {
  id: number;
  title: string;
  content: string;
  created_at?: string;
  tags?: string[];
}
export interface NotesResponse {
  total: number;
  items: NoteItem[];
}

export interface SectorSummary {
  sector?: string;
  name?: string;
  stock_count?: number;
  count?: number;
  avg_change_pct?: number;
  avg_score?: number;
  tier_a_count?: number;
  total_market_cap?: number;
}

export interface WatchlistItem {
  ticker: string;
  group_name?: string;
}

export interface HoldingItem {
  id: number;
  ticker: string;
  name?: string;
  quantity?: number;
  avg_price?: number;
  current_price?: number;
  signal_label?: 'BUY' | 'HOLD' | 'SELL' | 'WATCH';
}

// ── ML API (8001) hooks ──────────────────────────────────────────────────────

export function useRecommendations(params: {
  cohort?: string;
  diversify?: string;
  top_k?: number;
  date?: string;
  sector?: string;
  min_score?: number;
}) {
  return useQuery({
    queryKey: ['recommendations', params],
    queryFn: () => api.get<{ items: StockItem[]; meta?: unknown }>('/api/v1/stocks/recommendations', params),
    staleTime: 60_000,
  });
}

export function useMarketRegime(model_version: string = 'latest') {
  return useQuery({
    queryKey: ['market_regime', model_version],
    queryFn: () => api.get<MarketRegime>('/api/v1/market/regime', { model_version }),
    staleTime: 300_000,
  });
}

export function useStockSearch(q: string) {
  return useQuery({
    queryKey: ['search', q],
    queryFn: () => api.get<{ items: StockItem[] }>('/api/v1/stocks/search', { q, limit: 20 }),
    enabled: q.length > 0,
    staleTime: 30_000,
  });
}

export function useStockHistory(ticker: string, start?: string, end?: string) {
  return useQuery({
    queryKey: ['history', ticker, start, end],
    queryFn: () => api.get<HistoryResponse>(`/api/v1/stocks/${ticker}/history`, {
      start_date: start, end_date: end,
    }),
    enabled: !!ticker,
  });
}

export function useStockOutcome(ticker: string) {
  return useQuery({
    queryKey: ['outcome', ticker],
    queryFn: () => api.get<OutcomeResponse>(`/api/v1/stocks/${ticker}/outcome`),
    enabled: !!ticker,
    retry: false,
  });
}

export function useStockRadar(ticker: string) {
  return useQuery({
    queryKey: ['radar', ticker],
    queryFn: () => api.get<RadarResponse>(`/api/v1/stocks/${ticker}/radar`),
    enabled: !!ticker,
    retry: false,
  });
}

export function useStockFairValue(ticker: string) {
  return useQuery({
    queryKey: ['fairvalue', ticker],
    queryFn: () => api.get<FairValueResponse>(`/api/v1/stocks/${ticker}/fairvalue`),
    enabled: !!ticker,
    retry: false,
  });
}

export function useStockDividend(ticker: string) {
  return useQuery({
    queryKey: ['dividend', ticker],
    queryFn: () => api.get<DividendResponse>(`/api/v1/stocks/${ticker}/dividend`),
    enabled: !!ticker,
    retry: false,
  });
}

export function useStockPeers(ticker: string, limit = 8) {
  return useQuery({
    queryKey: ['peers', ticker, limit],
    queryFn: () => api.get<{ items: StockItem[] }>(`/api/v1/stocks/${ticker}/peers`, { limit }),
    enabled: !!ticker,
    retry: false,
  });
}

export function useStockFinancials(ticker: string, limit = 12) {
  return useQuery({
    queryKey: ['financials', ticker, limit],
    queryFn: () => api.get<FinancialsResponse>(`/api/v1/finance/${ticker}`, { limit }),
    enabled: !!ticker,
    retry: false,
  });
}

// PRD §3.4 — 일자별 승부주 Top-5 이력
export interface WinnerStock {
  ticker: string;
  name: string;
  recommend_price?: number;
  score?: number;
  trend?: { short: 'up' | 'down' | 'neutral'; medium: 'up' | 'down' | 'neutral'; long: 'up' | 'down' | 'neutral' };
  cumulative_return_pct?: number;
  /** B62: fairvalue API 의 적정가 (목표가). NULL 가능. */
  target_price?: number | null;
}
export interface WinnerDateGroup {
  date: string;
  winners: WinnerStock[];
}
export function useWinnerHistory(days_back = 21, top_k = 5) {
  return useQuery({
    queryKey: ['winners', days_back, top_k],
    queryFn: () => api.get<{ model_version: string; items: WinnerDateGroup[] }>(
      '/api/v1/winners', { days_back, top_k },
    ),
    retry: false,
  });
}

export function useScreener(params: Record<string, string | number | undefined>) {
  return useQuery({
    queryKey: ['screener', params],
    queryFn: () => api.get<{ items: StockItem[] }>('/api/v1/screener', params),
    staleTime: 60_000,
  });
}

export function useSectorsSummary(date?: string) {
  return useQuery({
    queryKey: ['sectors_summary', date],
    queryFn: () => api.get<{ items: SectorSummary[] }>('/api/v1/stocks/sectors/summary', { date }),
    staleTime: 300_000,
  });
}

export function useCompare(tickers: string[], period: string = '1y') {
  return useQuery({
    queryKey: ['compare', tickers, period],
    queryFn: () => api.get<{ items: StockItem[] }>('/api/v1/compare', {
      tickers: tickers.join(','),
      period,
    }),
    enabled: tickers.length >= 2,
    staleTime: 60_000,
  });
}

export function useNewsFeed(params: {
  limit?: number;
  offset?: number;
  sentiment?: 'positive' | 'neutral' | 'negative';
  ticker?: string;
}) {
  return useQuery({
    queryKey: ['news_feed', params],
    queryFn: () => api.get<NewsFeedResponse>('/api/v1/news/feed', params),
    staleTime: 60_000,
  });
}

// /my/portfolio — PRD §3.6 보유 종목 CRUD
export function useMyPortfolio() {
  return useQuery({
    queryKey: ['my_portfolio'],
    queryFn: () =>
      api.get<{ items: HoldingItem[] }>('/users/me/portfolio/holdings').catch(() => ({ items: [] })),
    retry: false,
  });
}

export function useAddHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      ticker: string; quantity: number; avg_price: number;
      bought_at?: string; memo?: string;
    }) => api.post<unknown>('/users/me/portfolio/holdings', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['my_portfolio'] }),
  });
}

export function useDeleteHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<unknown>(`/users/me/portfolio/holdings/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['my_portfolio'] }),
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.get<{ items: unknown[]; unread_count: number }>('/users/notifications'),
    retry: false,
  });
}

// 투자노트 CRUD — /users/me/notes
export function useNotes() {
  return useQuery({
    queryKey: ['notes'],
    queryFn: () => api.get<NotesResponse>('/users/me/notes'),
    retry: false,
  });
}

export function useAddNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; content: string; tags?: string[] }) =>
      api.post<unknown>('/users/me/notes', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notes'] }),
  });
}

export function useDeleteNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<unknown>(`/users/me/notes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notes'] }),
  });
}

export function useBatchDiagnosis(tickers: string[]) {
  return useQuery({
    queryKey: ['batch_diagnosis', tickers],
    queryFn: () => api.post<unknown>('/api/v1/stocks/batch-diagnosis', { tickers }),
    enabled: tickers.length > 0,
    staleTime: 60_000,
  });
}

// ── Auth API (8000) hooks ────────────────────────────────────────────────────

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api.post<{ session_token: string; nickname: string }>('/auth/login', body),
    onSuccess: (data) => {
      // legacy 헤더 토큰 (응답 본문). 향후 백엔드가 cookie-only 로 전환하면 제거.
      // cookie 자체는 fetch credentials 'include' 가 자동 처리 — JS 가 set 할 필요 없음.
      if (data.session_token) setSessionToken(data.session_token);
      // cookie 모드용 nickname marker — JS 가 토큰을 못 읽으므로 별도 isLoggedIn 신호.
      setSessionNickname(data.nickname || null);
      qc.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (body: { email: string; password: string; nickname: string }) =>
      api.post<unknown>('/auth/register', body),
  });
}

// 이메일 중복확인 + 인증코드 발송 (email 은 쿼리 파라미터)
export function useCheckEmail() {
  return useMutation({
    mutationFn: (email: string) =>
      api.post<{ message: string }>('/auth/check-email', undefined, { email }),
  });
}

// 인증코드 확인
export function useVerifyCode() {
  return useMutation({
    mutationFn: (body: { email: string; code: string }) =>
      api.post<{ message: string }>('/auth/verify-code', body),
  });
}

export function useWatchlist(group_name?: string) {
  return useQuery({
    queryKey: ['watchlist', group_name],
    queryFn: () => api.get<{ items: WatchlistItem[]; total: number }>('/users/me/watchlist', { group_name }),
    retry: false,
  });
}

export function useWatchlistGroups() {
  return useQuery({
    queryKey: ['watchlist_groups'],
    queryFn: () => api.get<{ groups: { name: string; count: number }[]; total_groups: number }>('/users/me/watchlist/groups'),
    retry: false,
  });
}

export function useAddWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { ticker: string; group_name?: string }) =>
      api.post<unknown>('/users/me/watchlist', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });
}

export function useDeleteWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ticker: string) => api.delete<unknown>(`/users/me/watchlist/${ticker}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });
}

// 내 프로필 — /users/me (이메일·닉네임·코호트·가입일)
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api.get<{
      user_id: number; email: string; nickname: string;
      cohort: string | null; is_verified: boolean; created_at: string | null;
    }>('/users/me'),
    retry: false,
  });
}

export function useCohort() {
  return useQuery({
    queryKey: ['me_cohort'],
    queryFn: () => api.get<{ cohort: string | null }>('/users/me/cohort'),
    retry: false,
  });
}

export function useSetCohort() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cohort: string | null) =>
      api.put<unknown>('/users/me/cohort', { cohort }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me_cohort'] });
      qc.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return async () => {
    // 서버 측 세션 폐기 (cookie 모드: Set-Cookie max-age=0). 실패해도 클라이언트는 정리.
    try { await api.post('/auth/logout'); } catch { /* idempotent */ }
    clearSession();
    qc.clear();
  };
}

/**
 * @tanstack/vue-query 기반 SWR 캐시 레이어
 * - versions, sectors: staleTime 5분 (거의 안 바뀜)
 * - recommendations: staleTime 60초 (Redis TTL 맞춤)
 * - stockDetail: staleTime 30초
 */
import { useQuery } from '@tanstack/vue-query'
import { stocksApi } from '@/api/stocks'
import api from '@/api/axios.js'

// ── 버전 목록 (5분) ──────────────────────────────────────────────────────────
export function useVersions() {
  return useQuery({
    queryKey: ['versions'],
    queryFn: () => stocksApi.getVersions().then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

// ── 섹터 목록 (5분) ──────────────────────────────────────────────────────────
export function useSectors() {
  return useQuery({
    queryKey: ['sectors'],
    queryFn: () => api.get('/stocks/sectors/summary').then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

// ── 종목 추천 (60초) ──────────────────────────────────────────────────────────
export function useRecommendations(paramsRef) {
  return useQuery({
    queryKey: ['recommendations', paramsRef],
    queryFn: () => stocksApi.getRecommendations(paramsRef.value ?? paramsRef).then(r => r.data),
    staleTime: 60 * 1000,
  })
}

// ── 종목 상세 (30초) ─────────────────────────────────────────────────────────
export function useStockDetail(tickerRef) {
  return useQuery({
    queryKey: ['stockDetail', tickerRef],
    queryFn: () => api.get(`/stocks/${tickerRef.value ?? tickerRef}`).then(r => r.data),
    staleTime: 30 * 1000,
    enabled: Boolean(tickerRef.value ?? tickerRef),
  })
}

// ── 뉴스 피드 (30초) ─────────────────────────────────────────────────────────
export function useNewsFeed(paramsRef) {
  return useQuery({
    queryKey: ['news', paramsRef],
    queryFn: () => api.get('/news/feed', { params: paramsRef.value ?? paramsRef }).then(r => r.data),
    staleTime: 30 * 1000,
  })
}

// ── 랭킹 (60초) ──────────────────────────────────────────────────────────────
export function useRanking(limitRef = 20) {
  return useQuery({
    queryKey: ['ranking', limitRef],
    queryFn: () => stocksApi.getRecommendations({ top_k: limitRef.value ?? limitRef }).then(r => r.data),
    staleTime: 60 * 1000,
  })
}

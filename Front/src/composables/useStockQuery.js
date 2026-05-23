/**
 * @tanstack/vue-query 기반 SWR 캐시 레이어
 * versions, sectors: staleTime 5분 / recommendations: 60초 / stockDetail: 30초
 */
import { useQuery } from '@tanstack/vue-query'
import { stocksApi } from '@/api/stocks.js'
import api from '@/api/axios.js'
import dbapi from '@/api/dbapi.js'

export function useVersions() {
  return useQuery({
    queryKey: ['versions'],
    queryFn: () => stocksApi.getVersions().then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

export function useSectors(paramsRef) {
  return useQuery({
    queryKey: ['sectors', paramsRef],
    queryFn: () => stocksApi.getSectorsSummary(paramsRef?.value ?? paramsRef ?? {}).then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

export function useRecommendations(paramsRef) {
  return useQuery({
    queryKey: ['recommendations', paramsRef],
    queryFn: () => stocksApi.getRecommendations(paramsRef?.value ?? paramsRef).then(r => r.data),
    staleTime: 60 * 1000,
  })
}

export function useStockDetail(tickerRef) {
  return useQuery({
    queryKey: ['stockDetail', tickerRef],
    queryFn: () => api.get(`/stocks/${tickerRef?.value ?? tickerRef}`).then(r => r.data),
    staleTime: 30 * 1000,
    enabled: Boolean(tickerRef?.value ?? tickerRef),
  })
}

export function useNewsFeed(paramsRef) {
  return useQuery({
    queryKey: ['news', paramsRef],
    queryFn: () => dbapi.get('/api/v1/news/feed', { params: paramsRef?.value ?? paramsRef }).then(r => r.data),
    staleTime: 30 * 1000,
  })
}

export function useRanking(limitRef = 20) {
  return useQuery({
    queryKey: ['ranking', limitRef],
    queryFn: () => stocksApi.getRecommendations({ top_k: limitRef?.value ?? limitRef }).then(r => r.data),
    staleTime: 60 * 1000,
  })
}

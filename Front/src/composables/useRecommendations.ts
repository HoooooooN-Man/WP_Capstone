// UX W3 — RecommendView 의 Vue Query wrapper.
// store 신설 안 함 (Vue Query 단독), URL query 동기.
// 캐시 키에 meta.model_version 포함 — 백엔드 AB_SPLIT 자동 전환 시 invalidate.

import { computed, type Ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
// @ts-ignore — 기존 axios.js 캡스톤 잔재 (Back/db 라우터)
import api from '@/api/axios'

export type DiversifyMode = 'none' | 'correlation' | 'sector' | 'embedding'
export type Cohort = 'balanced' | 'growth' | 'dividend' | 'short_term' | 'beginner'

export interface RecommendItem {
  ticker: string
  name: string
  sector?: string | null
  score: number
  tier: 'A' | 'B' | 'C' | 'D'
  rank_in_date?: number
  total_in_date?: number
}

export interface RecommendMeta {
  model_version?: string | null
  cohort?: Cohort | null
  diversify?: DiversifyMode | null
  market_regime?: 'normal' | 'extreme_volatility' | string | null
  as_of_date?: string | null
  is_advice?: boolean
  impression_id?: string | null
}

export interface RecommendResponse {
  date?: string
  model_version?: string
  total?: number
  items: RecommendItem[]
  meta?: RecommendMeta
}

export interface UseRecommendationsParams {
  topK?:      Ref<number>
  diversify?: Ref<DiversifyMode>
  cohort?:    Ref<Cohort | null>
}

const FIVE_MIN = 5 * 60 * 1000

export function useRecommendations(params: UseRecommendationsParams = {}) {
  const topK      = params.topK
  const diversify = params.diversify
  const cohort    = params.cohort

  const query = useQuery<RecommendResponse>({
    queryKey: computed(() => ['recommendations', {
      top_k:     topK?.value ?? 20,
      diversify: diversify?.value ?? 'none',
      cohort:    cohort?.value ?? null,
    }]) as any,
    queryFn: async () => {
      const queryParams: Record<string, string> = {
        top_k: String(topK?.value ?? 20),
      }
      const div = diversify?.value
      if (div && div !== 'none') queryParams.diversify = div
      if (cohort?.value)         queryParams.cohort    = cohort.value
      const { data } = await api.get('/stocks/recommendations', { params: queryParams })
      return data as RecommendResponse
    },
    staleTime: FIVE_MIN,
    retry: 1,
    refetchOnWindowFocus: false,
  })

  const items = computed<RecommendItem[]>(() => query.data.value?.items ?? [])
  const meta  = computed<RecommendMeta>(() => query.data.value?.meta ?? {})
  const total = computed<number>(() => items.value.length)

  return {
    query,
    items,
    meta,
    total,
    isLoading: query.isLoading,
    isError:   query.isError,
    error:     query.error,
    refetch:   query.refetch,
  }
}

// ── 한국어 매핑 (RecommendView·MetaBadge 공용) ───────────────────────────────

export const COHORT_LABEL: Record<string, string> = {
  balanced:   '균형',
  growth:     '성장',
  dividend:   '배당',
  short_term: '단타',
  beginner:   '입문',
}

export const DIVERSIFY_LABEL: Record<string, string> = {
  none:        '기본',
  correlation: '상관',
  sector:      '섹터',
  embedding:   '임베딩',
}

export function formatAsOfDate(iso: string | null | undefined): string {
  if (!iso) return ''
  // "2026-04-29" → "4월 29일 기준"
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return iso
  return `${parseInt(m[2], 10)}월 ${parseInt(m[3], 10)}일 기준`
}

// UX W5 — 5 cohort 메타 (한국어·아이콘·설명). CohortCard·CohortPicker 공용.
// 백엔드 차기 W2 코호트 정책 그대로 매핑.

export type CohortKey = 'balanced' | 'growth' | 'dividend' | 'short_term' | 'beginner'

export interface CohortMeta {
  key:         CohortKey
  label:       string
  icon:        string                       // primeicons class
  description: string
}

export const COHORT_META: readonly CohortMeta[] = [
  { key: 'balanced',   label: '균형', icon: 'pi-chart-bar',
    description: '안정과 성장의 균형을 추구합니다.' },
  { key: 'growth',     label: '성장', icon: 'pi-chart-line',
    description: '높은 성장 가능성 종목을 우선 추천합니다.' },
  { key: 'dividend',   label: '배당', icon: 'pi-wallet',
    description: '배당 수익을 우선합니다.' },
  { key: 'short_term', label: '단타', icon: 'pi-bolt',
    description: '단기 매매에 적합한 종목입니다.' },
  { key: 'beginner',   label: '입문', icon: 'pi-graduation-cap',
    description: '투자 입문자에게 적합한 안정적 종목입니다.' },
]

export const COHORT_BY_KEY: Record<CohortKey, CohortMeta> =
  COHORT_META.reduce((acc, m) => ({ ...acc, [m.key]: m }), {} as any)

export function getCohortMeta(key: CohortKey | string | null | undefined): CohortMeta | null {
  if (!key) return null
  return COHORT_BY_KEY[key as CohortKey] ?? null
}

/**
 * api/transparency.ts
 * ===================
 * Tier 1.5 (PRD §3.5) — 박제된 holdout·Model Card 결과 fetch.
 */
import api from './axios'

export interface HoldoutSummary {
  available: boolean
  ece: number | null
  brier: number | null
  sealed_at: string | null
  message: string | null
}

export interface AblationCandidate {
  name: string
  n: number
  auc: number
  ece: number
  brier: number
}

export interface AblationDelta {
  delta_auc: number
  delta_ece: number
  delta_brier: number
  interpretation: string
}

export interface HoldoutFull {
  available: boolean
  message?: string
  archive_dir?: string
  report?: any
  calibration?: any
  ablation?: {
    n_observations: number
    candidates: AblationCandidate[]
    ensemble_vs_lgbm: AblationDelta
    policy?: string
  } | null
}

export interface ModelCardResponse {
  available: boolean
  markdown: string | null
  message: string | null
}

export async function fetchHoldoutSummary(): Promise<HoldoutSummary> {
  const r = await api.get<HoldoutSummary>('/transparency/holdout/summary')
  return r.data
}

export async function fetchHoldoutFull(): Promise<HoldoutFull> {
  const r = await api.get<HoldoutFull>('/transparency/holdout')
  return r.data
}

export async function fetchModelCard(): Promise<ModelCardResponse> {
  const r = await api.get<ModelCardResponse>('/transparency/model-card')
  return r.data
}

import api from './axios'

// /screener 엔드포인트가 없으므로 /stocks/recommendations 으로 연결
// 지원 파라미터: model_version, date, sector, min_score, top_k
// 미지원 파라미터: tier(→min_score 변환), sort_by(→클라이언트 정렬), 재무 필터(미지원)

const TIER_MIN_SCORE = { A: 80, B: 60, C: 40, D: 0 }

export const screenerApi = {
  getScreener: (params) => {
    const mapped = {}

    // ── 백엔드 지원 파라미터 직접 전달 ──────────────────
    if (params.model_version) mapped.model_version = params.model_version
    if (params.date)          mapped.date          = params.date
    if (params.sector)        mapped.sector        = params.sector

    // tier → min_score 변환 (직접 지정한 min_score와 더 높은 값 사용)
    const tierMin  = params.tier ? (TIER_MIN_SCORE[params.tier] ?? 0) : 0
    const minScore = Math.max(Number(params.min_score ?? 0), tierMin)
    if (minScore > 0) mapped.min_score = minScore

    // limit → top_k (0=전체, 최대 500)
    mapped.top_k = params.limit ? Math.min(Number(params.limit), 500) : 100

    return api.get('/stocks/recommendations', { params: mapped })
  },
}

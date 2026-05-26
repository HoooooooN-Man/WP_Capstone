import api from './axios'

// /screener 엔드포인트가 없으므로 /stocks/recommendations 으로 연결
// 파라미터 매핑: limit → top_k, 재무 필터는 백엔드 미지원으로 제외
export const screenerApi = {
  getScreener: (params) => {
    const mapped = {}
    if (params.model_version) mapped.model_version = params.model_version
    if (params.date)          mapped.date          = params.date
    if (params.sector)        mapped.sector        = params.sector
    if (params.min_score)     mapped.min_score     = params.min_score
    if (params.limit)         mapped.top_k         = params.limit
    return api.get('/stocks/recommendations', { params: mapped })
  },
}

import api from './axios'
import dbapi from './dbapi'

export const portfolioApi = {
  // ── 보유 종목 CRUD (dbapi 8000) ─────────────────────────────
  getHoldings:   ()     => dbapi.get('/api/v1/users/me/portfolio/holdings'),
  addHolding:    (data) => dbapi.post('/api/v1/users/me/portfolio/holdings', data),
  deleteHolding: (id)   => dbapi.delete(`/api/v1/users/me/portfolio/holdings/${id}`),

  // /portfolio/kospi200 엔드포인트가 없으므로 /stocks/recommendations 으로 우회
  // type='growth' → ML 점수 상위 10개 / type='stable' → 최소 60점 이상 상위 10개
  getKospi200: (type, ver) => {
    const params = { model_version: ver, top_k: 10 }
    if (type === 'stable') params.min_score = 60
    return api.get('/stocks/recommendations', { params }).then(res => {
      const items = (res.data.items ?? []).map((item, i) => ({ ...item, rank: i + 1 }))
      return { ...res, data: { ...res.data, items } }
    })
  },
  getBacktestSummary: () => api.get('/portfolio/backtest/summary'),
  getBacktestMonthly: () => api.get('/portfolio/backtest/monthly'),
}

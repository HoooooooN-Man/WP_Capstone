import api from './axios'
import dbapi from './dbapi'

export const stocksApi = {
  getVersions:        ()                      => api.get('/stocks/versions'),
  getDates:           (ver)                   => api.get('/stocks/dates', { params: { model_version: ver } }),
  getRecommendations: (params)                => api.get('/stocks/recommendations', { params }),
  getSectorsSummary:  (params)                => api.get('/stocks/sectors/summary', { params }),
  searchStocks:       (q, ver, limit = 20)    => api.get('/stocks/search', { params: { q, model_version: ver, limit } }),
  getHistory:         (ticker, params)        => api.get(`/stocks/${ticker}/history`, { params }),
  getCompare:         (tickers, ver, period)  => api.get('/compare', { params: { tickers, model_version: ver, period } }),
  getRisingStocks:    (params)                => api.get('/stocks/rising', { params }),
  getPopularPosts:    (limit = 20)            => dbapi.get('/api/v1/board/popular', { params: { limit } }),
}

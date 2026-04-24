import api from './axios'

export const financeApi = {
  getLatest:  (ticker)        => api.get(`/finance/${ticker}/latest`),
  getHistory: (ticker, limit) => api.get(`/finance/${ticker}`, { params: { limit } }),
}

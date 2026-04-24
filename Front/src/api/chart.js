import api from './axios'

export const chartApi = {
  getCandles: (ticker, period = '1y') => api.get(`/chart/${ticker}`, { params: { period } }),
}

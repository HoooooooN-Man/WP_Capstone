import api from './axios'

export const portfolioApi = {
  getKospi200:        (type, ver) => api.get('/portfolio/kospi200', { params: { type, model_version: ver } }),
  getBacktestSummary: ()          => api.get('/portfolio/backtest/summary'),
  getBacktestMonthly: ()          => api.get('/portfolio/backtest/monthly'),
}

import api from './axios'

export const screenerApi = {
  getScreener: (params) => api.get('/screener', { params }),
}

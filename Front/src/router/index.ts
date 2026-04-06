import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    {
      path: '/recommend',
      name: 'recommend',
      component: () => import('../views/RecommendView.vue'),
    },
    {
      path: '/screener',
      name: 'screener',
      component: () => import('../views/ScreenerView.vue'),
    },
    {
      path: '/stock/:ticker',
      name: 'stock-detail',
      component: () => import('../views/StockDetailView.vue'),
    },
    {
      path: '/compare',
      name: 'compare',
      component: () => import('../views/CompareView.vue'),
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router

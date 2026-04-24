import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/',              name: 'Home',        component: () => import('@/views/HomeView.vue') },
  { path: '/stocks',        name: 'Stocks',      component: () => import('@/views/StocksView.vue') },
  { path: '/stocks/:ticker',name: 'StockDetail', component: () => import('@/views/StockDetailView.vue') },
  { path: '/screener',      name: 'Screener',    component: () => import('@/views/ScreenerView.vue') },
  { path: '/portfolio',     name: 'Portfolio',   component: () => import('@/views/PortfolioView.vue') },
  { path: '/compare',       name: 'Compare',     component: () => import('@/views/CompareView.vue') },
  { path: '/my',            name: 'MyPage',      component: () => import('@/views/MyPageView.vue'), meta: { requiresAuth: true } },
  { path: '/login',         name: 'Login',       component: () => import('@/views/LoginView.vue') },
  { path: '/register',      name: 'Register',    component: () => import('@/views/RegisterView.vue') },
  // 기존 경로 호환
  { path: '/recommend',     redirect: '/stocks' },
  { path: '/stock/:ticker', redirect: to => `/stocks/${to.params.ticker}` },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router

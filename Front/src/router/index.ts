import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

// 다른 사람이 작성한 HomeView 임포트 (경로 확인 필요)
import HomeView from '@/page/main/HomeView.vue'; 

const routes: Array<RouteRecordRaw> = [
  { 
    path: '/login', 
    name: 'Login',
    component: () => import('@/page/auth/Login.vue') 
  },
  { 
    path: '/register', 
    name: 'Register',
    component: () => import('@/page/auth/Register.vue') 
  },
  { 
    path: '/reset-password', 
    name: 'ResetPassword',
    component: () => import('@/page/auth/ResetPassword.vue'),
    meta: { requiresAuth: true }
  },
  { 
    path: '/',
    name: 'MainView', 
    component: HomeView 
  },
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

  { 
    path: '/', 
    redirect: '/home' 
  },

  {
    path: '/test',
    name: 'test',
    component: () => import('../page/main/test.vue'),
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    alert('로그인이 필요한 페이지입니다.');
    next('/login');
  } else {
    next();
  }
});

export default router;
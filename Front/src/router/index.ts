import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/page/main/Home.vue'),
  },
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
    redirect: '/home' 
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    alert('로그인이 필요한 페이지입니다.')
    next('/login')
  } else {
    next()
  }
})

export default router;
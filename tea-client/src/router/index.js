import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue')
  },
  {
    path: '/status',
    name: 'Status',
    component: () => import('../views/StatusView.vue')
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: () => import('../views/StatisticsView.vue')
  },
  {
    path: '/tea-types',
    name: 'TeaTypes',
    component: () => import('../views/TeaTypesView.vue'),
    meta: { requiresAdmin: true }
  },
  {
    path: '/events',
    name: 'Events',
    component: () => import('../views/EventsView.vue'),
    meta: { requiresAdmin: true }
  },
  {
    path: '/database',
    name: 'Database',
    component: () => import('../views/DatabaseView.vue'),
    meta: { requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
})

export default router

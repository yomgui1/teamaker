import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/status'
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
  },
  {
    path: '/coffee',
    name: 'Coffee',
    component: () => import('../views/CoffeeView.vue')
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/status'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.checking) {
    await auth.checkAuth()
  }
  if (!auth.initialized && to.name !== 'Login') {
    return { name: 'Login' }
  }
  if (!auth.authenticated && to.meta.requiresAdmin) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (auth.authenticated && to.name === 'Login') {
    return { name: 'Status' }
  }
})

export default router

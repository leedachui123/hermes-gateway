import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './views/LoginView.vue'
import DashboardView from './views/DashboardView.vue'
import UserManagementView from './views/UserManagementView.vue'

const routes = [
  { path: '/app/login', name: 'login', component: LoginView },
  { path: '/app/', name: 'dashboard', component: DashboardView, meta: { requiresAuth: true } },
  { path: '/app/admin/users', name: 'users', component: UserManagementView, meta: { requiresAuth: true, requiresAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  if (!to.meta.requiresAuth) return next()
  try {
    const resp = await fetch('/api/me', { credentials: 'include' })
    if (!resp.ok) throw new Error('Not authenticated')
    const user = await resp.json()
    if (to.meta.requiresAdmin && user.role !== 'admin') {
      next('/app/')
      return
    }
    next()
  } catch {
    next('/app/login')
  }
})

export default router

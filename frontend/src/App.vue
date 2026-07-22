<template>
  <div v-if="!isLoginPage">
    <nav class="navbar">
      <router-link to="/app/" class="brand">🔐 Hermes Gateway</router-link>
      <div class="nav-links">
        <router-link to="/app/">Dashboard</router-link>
        <router-link v-if="user?.role === 'admin'" to="/app/admin/users">User Management</router-link>
      </div>
      <div class="nav-right">
        <span class="user-info">👤 {{ user?.username }}</span>
        <button class="btn-logout" @click="handleLogout">Logout</button>
      </div>
    </nav>
    <div class="container">
      <router-view />
    </div>
    <div class="footer">Hermes Gateway v1.0</div>
  </div>
  <router-view v-else />
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from './api.js'

export default {
  setup() {
    const router = useRouter()
    const route = useRoute()
    const user = ref(null)

    const isLoginPage = computed(() => route.path === '/app/login')

    onMounted(async () => {
      if (!isLoginPage.value) {
        try {
          user.value = await api.me()
        } catch {
          router.push('/app/login')
        }
      }
    })

    async function handleLogout() {
      await api.logout()
      user.value = null
      router.push('/app/login')
    }

    return { user, isLoginPage, handleLogout }
  },
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f0f2f5;
  min-height: 100vh;
  color: #333;
}
.navbar {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 32px;
}
.brand {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  text-decoration: none;
}
.nav-links { display: flex; gap: 24px; flex: 1; }
.nav-links a {
  font-size: 14px;
  color: #555;
  text-decoration: none;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: all .2s;
}
.nav-links a:hover, .nav-links a.router-link-exact-active {
  color: #1677ff;
  border-bottom-color: #1677ff;
}
.nav-right { display: flex; align-items: center; gap: 12px; }
.user-info { font-size: 14px; color: #555; }
.btn-logout {
  padding: 4px 12px; font-size: 13px;
  background: transparent; border: 1px solid #d9d9d9; border-radius: 6px;
  cursor: pointer; color: #555;
}
.btn-logout:hover { color: #ff4d4f; border-color: #ff4d4f; }
.container { max-width: 1000px; margin: 32px auto; padding: 0 24px; }
.footer { text-align: center; font-size: 12px; color: #999; margin-top: 48px; padding-bottom: 24px; }
.card { background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.page-header h1 { font-size: 20px; font-weight: 600; }
.btn {
  padding: 8px 20px; font-size: 14px; font-weight: 500;
  border: none; border-radius: 8px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 4px;
}
.btn-primary { background: #1677ff; color: #fff; }
.btn-primary:hover { background: #4096ff; }
.btn-danger { background: #ff4d4f; color: #fff; }
.btn-danger:hover { background: #ff7875; }
.btn-default { background: #f5f5f5; color: #333; border: 1px solid #d9d9d9; }
.btn-default:hover { background: #e8e8e8; }
.btn-sm { padding: 4px 12px; font-size: 13px; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #f0f0f0; }
th { font-weight: 500; color: #888; font-size: 13px; }
tr:hover td { background: #fafafa; }
.badge {
  display: inline-block; padding: 2px 10px; font-size: 12px;
  font-weight: 500; border-radius: 10px;
}
.badge-admin { background: #e6f4ff; color: #1677ff; }
.badge-user { background: #f5f5f5; color: #666; }
.badge-active { background: #f6ffed; color: #52c41a; }
.badge-inactive { background: #fff2f0; color: #ff4d4f; }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: #fff; border-radius: 12px; padding: 24px;
  width: 400px; max-width: 90vw; box-shadow: 0 8px 24px rgba(0,0,0,.15);
}
.modal-header { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.modal-body { margin-bottom: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 6px; color: #555; }
.form-control {
  width: 100%; padding: 10px 12px; border: 1px solid #d9d9d9;
  border-radius: 8px; font-size: 14px;
}
.form-control:focus { border-color: #4096ff; outline: none; box-shadow: 0 0 0 2px rgba(64,150,255,.2); }
.form-error { font-size: 13px; color: #ff4d4f; margin-top: 4px; }
.loading { text-align: center; padding: 48px 0; color: #999; font-size: 14px; }
.empty { text-align: center; padding: 48px 0; color: #999; }
.toast {
  position: fixed; top: 16px; right: 16px; z-index: 2000;
  padding: 12px 20px; border-radius: 8px; font-size: 14px;
  color: #fff; box-shadow: 0 4px 12px rgba(0,0,0,.15);
  animation: fadeIn .3s ease;
}
@keyframes fadeIn { from { opacity: 0; transform: translateX(40px); } to { opacity: 1; transform: translateX(0); } }
.toast-success { background: #52c41a; }
.toast-error { background: #ff4d4f; }
</style>

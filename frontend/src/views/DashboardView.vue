<template>
  <div class="card">
    <div class="page-header">
      <h1>Dashboard</h1>
      <a v-if="user?.role === 'admin'" href="/app/admin/users" class="btn btn-primary">User Management</a>
    </div>
    <div class="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.totalUsers }}</div>
        <div class="stat-label">Total Users</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.adminCount }}</div>
        <div class="stat-label">Admins</div>
      </div>
    </div>
    <div style="margin-top:24px;padding:16px;background:#f6ffed;border-radius:8px;border:1px solid #b7eb8f">
      <p style="font-size:14px;color:#333">✅ Gateway is running. Hermes backend is available at the proxy endpoint.</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

export default {
  setup() {
    const user = ref(null)
    const stats = ref({ totalUsers: 0, adminCount: 0 })

    onMounted(async () => {
      try {
        user.value = await api.me()
        if (user.value.role === 'admin') {
          const data = await api.listUsers()
          stats.value.totalUsers = data.users.length
          stats.value.adminCount = data.users.filter(u => u.role === 'admin').length
        }
      } catch (e) {
        console.error('Failed to load dashboard', e)
      }
    })

    return { user, stats }
  },
}
</script>

<style scoped>
.stats { display: flex; gap: 16px; }
.stat-card {
  flex: 1; background: #fafafa; border: 1px solid #e8e8e8;
  border-radius: 8px; padding: 24px; text-align: center;
}
.stat-value { font-size: 32px; font-weight: 700; color: #1677ff; }
.stat-label { font-size: 14px; color: #888; margin-top: 4px; }
</style>

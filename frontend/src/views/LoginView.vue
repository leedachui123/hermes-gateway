<template>
  <div class="login-page">
    <div class="login-card">
      <h1>🔐 Hermes Gateway</h1>
      <p class="subtitle">Sign in to continue</p>
      <div v-if="error" class="error-msg">{{ error }}</div>
      <form @submit.prevent="handleLogin">
        <label for="username">Username</label>
        <input id="username" v-model="username" type="text" class="form-control" autocomplete="username" required autofocus>
        <label for="password">Password</label>
        <input id="password" v-model="password" type="password" class="form-control" autocomplete="current-password" required>
        <button type="submit" class="btn btn-primary login-btn" :disabled="loading">
          {{ loading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'

export default {
  setup() {
    const router = useRouter()
    const username = ref('')
    const password = ref('')
    const error = ref('')
    const loading = ref(false)

    async function handleLogin() {
      error.value = ''
      loading.value = true
      try {
        const resp = await api.login(username.value, password.value)
        const data = await resp.json()
        if (data.status === 'ok') {
          router.push('/app/')
        } else {
          error.value = data.detail || 'Invalid username or password'
        }
      } catch (e) {
        error.value = e.message
      } finally {
        loading.value = false
      }
    }

    return { username, password, error, loading, handleLogin }
  },
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: #f0f2f5;
}
.login-card {
  background: #fff; border-radius: 12px; padding: 40px;
  width: 360px; box-shadow: 0 2px 12px rgba(0,0,0,.08);
}
.login-card h1 { font-size: 22px; font-weight: 600; text-align: center; margin-bottom: 8px; }
.subtitle { font-size: 14px; color: #666; text-align: center; margin-bottom: 28px; }
.error-msg {
  background: #fff2f0; border: 1px solid #ffccc7; border-radius: 6px;
  padding: 8px 12px; margin-bottom: 16px; font-size: 13px; color: #cf1322;
}
label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 6px; }
.login-btn {
  width: 100%; margin-top: 8px; justify-content: center;
}
</style>

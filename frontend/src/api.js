const BASE = '/api'

async function request(path, opts = {}) {
  const resp = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  })
  const data = resp.headers.get('content-type')?.includes('json')
    ? await resp.json()
    : null
  if (!resp.ok) {
    const msg = data?.detail || data?.error || `HTTP ${resp.status}`
    if (resp.status === 401) {
      // Redirect to login if the API says we're unauthorized
      window.location.href = '/app/login'
      throw new Error('Session expired')
    }
    throw new Error(msg)
  }
  return data
}

export const api = {
  login(username, password) {
    return fetch(`${BASE}/login`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
      redirect: 'manual',
    })
  },

  logout() {
    return fetch(`${BASE}/logout`, {
      method: 'POST',
      credentials: 'include',
      redirect: 'manual',
    })
  },

  me() {
    return request('/me')
  },

  listUsers() {
    return request('/admin/users')
  },

  createUser(username, password, role) {
    return request('/admin/users', {
      method: 'POST',
      body: JSON.stringify({ username, password, role }),
    })
  },

  updateUser(id, data) {
    return request(`/admin/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  deleteUser(id) {
    return request(`/admin/users/${id}`, { method: 'DELETE' })
  },

  resetPassword(id, password) {
    return request(`/admin/users/${id}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ password }),
    })
  },

  changePassword(oldPassword, newPassword) {
    return request('/me/password', {
      method: 'PUT',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    })
  },
}

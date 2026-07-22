<template>
  <div class="card">
    <div class="page-header">
      <h1>User Management</h1>
      <button class="btn btn-primary" @click="openAddModal">+ Add User</button>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Username</th><th>Role</th><th>Status</th><th>Created</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="6" class="loading">Loading...</td></tr>
          <tr v-else-if="users.length === 0"><td colspan="6" class="empty">No users yet.</td></tr>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.id }}</td>
            <td><strong>{{ u.username }}</strong></td>
            <td><span class="badge" :class="u.role === 'admin' ? 'badge-admin' : 'badge-user'">{{ u.role === 'admin' ? 'Admin' : 'User' }}</span></td>
            <td><span class="badge" :class="u.is_active ? 'badge-active' : 'badge-inactive'">{{ u.is_active ? 'Active' : 'Disabled' }}</span></td>
            <td>{{ u.created_at?.slice(0, 10) || '-' }}</td>
            <td>
              <div class="actions">
                <button class="btn btn-default btn-sm" @click="openEditModal(u)">Edit</button>
                <button class="btn btn-default btn-sm" @click="openResetPwModal(u)">Reset PW</button>
                <button class="btn btn-danger btn-sm" @click="openDeleteModal(u)" :disabled="u.username === currentUser">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Add Modal -->
  <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
    <div class="modal">
      <div class="modal-header">Add User</div>
      <div class="modal-body">
        <div class="form-group">
          <label>Username</label>
          <input v-model="addForm.username" class="form-control" autocomplete="off">
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="addForm.password" type="password" class="form-control" autocomplete="new-password">
          <div class="form-error">Minimum 6 characters</div>
        </div>
        <div class="form-group">
          <label>Role</label>
          <select v-model="addForm.role" class="form-control">
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div v-if="addError" class="form-error">{{ addError }}</div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-default" @click="showAddModal = false">Cancel</button>
        <button class="btn btn-primary" @click="handleAdd" :disabled="addLoading">
          {{ addLoading ? 'Creating...' : 'Create' }}
        </button>
      </div>
    </div>
  </div>

  <!-- Edit Modal -->
  <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
    <div class="modal">
      <div class="modal-header">Edit User</div>
      <div class="modal-body">
        <div class="form-group">
          <label>Username</label>
          <input v-model="editForm.username" class="form-control">
        </div>
        <div class="form-group">
          <label>Role</label>
          <select v-model="editForm.role" class="form-control">
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div class="form-group">
          <label>Status</label>
          <select v-model="editForm.isActive" class="form-control">
            <option :value="true">Active</option>
            <option :value="false">Disabled</option>
          </select>
        </div>
        <div v-if="editError" class="form-error">{{ editError }}</div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-default" @click="showEditModal = false">Cancel</button>
        <button class="btn btn-primary" @click="handleEdit" :disabled="editLoading">
          {{ editLoading ? 'Saving...' : 'Save' }}
        </button>
      </div>
    </div>
  </div>

  <!-- Reset Password Modal -->
  <div v-if="showResetPwModal" class="modal-overlay" @click.self="showResetPwModal = false">
    <div class="modal">
      <div class="modal-header">Reset Password — {{ resetPwTarget?.username }}</div>
      <div class="modal-body">
        <div class="form-group">
          <label>New Password</label>
          <input v-model="resetPwForm.password" type="password" class="form-control" autocomplete="new-password">
          <div class="form-error">Minimum 6 characters</div>
        </div>
        <div v-if="resetPwError" class="form-error">{{ resetPwError }}</div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-default" @click="showResetPwModal = false">Cancel</button>
        <button class="btn btn-primary" @click="handleResetPassword" :disabled="resetPwLoading">
          {{ resetPwLoading ? 'Resetting...' : 'Reset' }}
        </button>
      </div>
    </div>
  </div>

  <!-- Delete Modal -->
  <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
    <div class="modal">
      <div class="modal-header">Confirm Delete</div>
      <div class="modal-body">
        <p>Are you sure you want to delete <strong>{{ deleteTarget?.username }}</strong>?</p>
        <p style="margin-top:8px;font-size:13px;color:#888">This action cannot be undone.</p>
        <div v-if="deleteError" class="form-error" style="margin-top:12px">{{ deleteError }}</div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-default" @click="showDeleteModal = false">Cancel</button>
        <button class="btn btn-danger" @click="handleDelete" :disabled="deleteLoading">
          {{ deleteLoading ? 'Deleting...' : 'Delete' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

export default {
  setup() {
    const users = ref([])
    const loading = ref(true)
    const currentUser = ref('')

    // Add
    const showAddModal = ref(false)
    const addLoading = ref(false)
    const addError = ref('')
    const addForm = ref({ username: '', password: '', role: 'user' })

    // Edit
    const showEditModal = ref(false)
    const editLoading = ref(false)
    const editError = ref('')
    const editForm = ref({ id: null, username: '', role: 'user', isActive: true })

    // Reset PW
    const showResetPwModal = ref(false)
    const resetPwLoading = ref(false)
    const resetPwError = ref('')
    const resetPwTarget = ref(null)
    const resetPwForm = ref({ password: '' })

    // Delete
    const showDeleteModal = ref(false)
    const deleteLoading = ref(false)
    const deleteError = ref('')
    const deleteTarget = ref(null)

    async function loadUsers() {
      loading.value = true
      try {
        const data = await api.listUsers()
        users.value = data.users
      } catch (e) {
        console.error('Failed to load users', e)
      } finally {
        loading.value = false
      }
    }

    onMounted(async () => {
      try {
        const me = await api.me()
        currentUser.value = me.username
      } catch {}
      await loadUsers()
    })

    function openAddModal() {
      addForm.value = { username: '', password: '', role: 'user' }
      addError.value = ''
      showAddModal.value = true
    }

    async function handleAdd() {
      addError.value = ''
      if (!addForm.value.username) { addError.value = 'Username is required'; return }
      if (addForm.value.password.length < 6) { addError.value = 'Password must be at least 6 characters'; return }
      addLoading.value = true
      try {
        await api.createUser(addForm.value.username, addForm.value.password, addForm.value.role)
        showAddModal.value = false
        toast('User created')
        await loadUsers()
      } catch (e) { addError.value = e.message }
      finally { addLoading.value = false }
    }

    function openEditModal(u) {
      editForm.value = { id: u.id, username: u.username, role: u.role, isActive: !!u.is_active }
      editError.value = ''
      showEditModal.value = true
    }

    async function handleEdit() {
      editError.value = ''
      if (!editForm.value.username) { editError.value = 'Username cannot be empty'; return }
      editLoading.value = true
      try {
        await api.updateUser(editForm.value.id, {
          username: editForm.value.username,
          role: editForm.value.role,
          is_active: editForm.value.isActive,
        })
        showEditModal.value = false
        toast('User updated')
        await loadUsers()
      } catch (e) { editError.value = e.message }
      finally { editLoading.value = false }
    }

    function openResetPwModal(u) {
      resetPwTarget.value = u
      resetPwForm.value = { password: '' }
      resetPwError.value = ''
      showResetPwModal.value = true
    }

    async function handleResetPassword() {
      resetPwError.value = ''
      if (resetPwForm.value.password.length < 6) { resetPwError.value = 'Password must be at least 6 characters'; return }
      resetPwLoading.value = true
      try {
        await api.resetPassword(resetPwTarget.value.id, resetPwForm.value.password)
        showResetPwModal.value = false
        toast('Password reset')
      } catch (e) { resetPwError.value = e.message }
      finally { resetPwLoading.value = false }
    }

    function openDeleteModal(u) {
      deleteTarget.value = u
      deleteError.value = ''
      showDeleteModal.value = true
    }

    async function handleDelete() {
      deleteLoading.value = true
      try {
        await api.deleteUser(deleteTarget.value.id)
        showDeleteModal.value = false
        toast('User deleted')
        await loadUsers()
      } catch (e) { deleteError.value = e.message }
      finally { deleteLoading.value = false }
    }

    function toast(msg) {
      const el = document.createElement('div')
      el.className = 'toast toast-success'
      el.textContent = msg
      document.body.appendChild(el)
      setTimeout(() => el.remove(), 3000)
    }

    return {
      users, loading, currentUser,
      showAddModal, addLoading, addError, addForm, openAddModal, handleAdd,
      showEditModal, editLoading, editError, editForm, openEditModal, handleEdit,
      showResetPwModal, resetPwLoading, resetPwError, resetPwTarget, resetPwForm, openResetPwModal, handleResetPassword,
      showDeleteModal, deleteLoading, deleteError, deleteTarget, openDeleteModal, handleDelete,
    }
  },
}
</script>

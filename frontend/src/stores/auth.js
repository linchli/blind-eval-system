import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiLogin, apiGetMe } from '../api/index.js'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('blind_eval_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('blind_eval_user') || 'null'))
  const loading = ref(false)
  const error = ref('')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isGuest = computed(() => user.value?.role === 'guest')

  async function login(username, password) {
    loading.value = true
    error.value = ''
    try {
      const data = await apiLogin({ username, password })
      token.value = data.access_token
      user.value = { username: data.username, role: data.role, display_name: data.display_name }
      localStorage.setItem('blind_eval_token', data.access_token)
      localStorage.setItem('blind_eval_user', JSON.stringify(user.value))
      return true
    } catch (e) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('blind_eval_token')
    localStorage.removeItem('blind_eval_user')
  }

  return { token, user, loading, error, isLoggedIn, isAdmin, isGuest, login, logout }
})

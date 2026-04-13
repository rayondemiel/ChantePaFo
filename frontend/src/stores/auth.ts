import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('chantepafo_token'))
  const username = ref<string | null>(localStorage.getItem('chantepafo_username'))
  const userId = ref<string | null>(localStorage.getItem('chantepafo_userId'))

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(data: { token: string; username: string; user_id: string }) {
    token.value = data.token
    username.value = data.username
    userId.value = data.user_id
    localStorage.setItem('chantepafo_token', data.token)
    localStorage.setItem('chantepafo_username', data.username)
    localStorage.setItem('chantepafo_userId', data.user_id)
  }

  function clearAuth() {
    token.value = null
    username.value = null
    userId.value = null
    localStorage.removeItem('chantepafo_token')
    localStorage.removeItem('chantepafo_username')
    localStorage.removeItem('chantepafo_userId')
  }

  async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const headers = new Headers(options.headers)
    if (token.value) {
      headers.set('Authorization', `Bearer ${token.value}`)
    }
    headers.set('Content-Type', 'application/json')
    return fetch(url, { ...options, headers })
  }

  return { token, username, userId, isLoggedIn, setAuth, clearAuth, authFetch }
})

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../../src/stores/auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('starts with null token', () => {
    const store = useAuthStore()
    expect(store.token).toBeNull()
    expect(store.isLoggedIn).toBe(false)
  })

  it('setAuth persists to localStorage', () => {
    const store = useAuthStore()
    store.setAuth({ token: 'abc', username: 'alice', user_id: 'u1' })
    expect(store.token).toBe('abc')
    expect(store.username).toBe('alice')
    expect(store.userId).toBe('u1')
    expect(store.isLoggedIn).toBe(true)
    expect(localStorage.getItem('chantepafo_token')).toBe('abc')
  })

  it('clearAuth removes from localStorage', () => {
    const store = useAuthStore()
    store.setAuth({ token: 'abc', username: 'alice', user_id: 'u1' })
    store.clearAuth()
    expect(store.token).toBeNull()
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.getItem('chantepafo_token')).toBeNull()
  })
})

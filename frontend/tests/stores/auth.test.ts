import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../../src/stores/auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
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

  it('authFetch attaches the bearer token when logged in', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response('{}', { status: 200 }))
    const store = useAuthStore()
    store.setAuth({ token: 'secret', username: 'alice', user_id: 'u1' })

    await store.authFetch('/api/rooms')

    expect(fetchSpy).toHaveBeenCalledOnce()
    const call = fetchSpy.mock.calls[0]
    const headers = (call[1] as RequestInit).headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer secret')
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('authFetch omits Authorization header when not logged in', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response('{}', { status: 200 }))
    const store = useAuthStore()

    await store.authFetch('/api/public', { method: 'POST', body: '{}' })

    const call = fetchSpy.mock.calls[0]
    const headers = (call[1] as RequestInit).headers as Headers
    expect(headers.get('Authorization')).toBeNull()
    expect(headers.get('Content-Type')).toBe('application/json')
    expect((call[1] as RequestInit).method).toBe('POST')
  })

  it('hydrates from localStorage on initial instantiation', () => {
    localStorage.setItem('chantepafo_token', 'persisted')
    localStorage.setItem('chantepafo_username', 'bob')
    localStorage.setItem('chantepafo_userId', 'u2')
    // Fresh Pinia — forces a new store instance to re-read localStorage
    setActivePinia(createPinia())
    const store = useAuthStore()
    expect(store.token).toBe('persisted')
    expect(store.username).toBe('bob')
    expect(store.userId).toBe('u2')
    expect(store.isLoggedIn).toBe(true)
  })
})

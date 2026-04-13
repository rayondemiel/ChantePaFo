import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import HomeView from '../../src/views/HomeView.vue'

// useSocket must be a no-op in tests (we don't want a real socket spun up)
vi.mock('../../src/composables/useSocket', () => ({
  useSocket: () => ({
    connect: vi.fn(),
    emit: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    disconnect: vi.fn(),
  }),
}))

async function mountHome() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: HomeView },
      { path: '/:code', component: { template: '<div>lobby</div>' } },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(HomeView, {
    global: { plugins: [router, createPinia()] },
  })
  return { wrapper, router }
}

describe('HomeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the hero and both create/join sections', async () => {
    const { wrapper } = await mountHome()
    expect(wrapper.text()).toContain('ChantePaFo')
    expect(wrapper.text()).toContain('Nouvelle room')
    expect(wrapper.text()).toContain('Code existant')
  })

  it('disables the create button until a host name is entered', async () => {
    const { wrapper } = await mountHome()
    const createBtn = wrapper.get('button.btn-primary')
    expect(createBtn.attributes('disabled')).toBeDefined()

    await wrapper.get('input[placeholder="Ton pseudo"]').setValue('Alice')
    expect(createBtn.attributes('disabled')).toBeUndefined()
  })

  it('persists the pseudo to localStorage via the watcher', async () => {
    const { wrapper } = await mountHome()
    await wrapper.get('input[placeholder="Ton pseudo"]').setValue('Alice')
    expect(localStorage.getItem('chantepafo.pseudo')).toBe('Alice')
  })

  it('hydrates the pseudo inputs from localStorage on mount', async () => {
    localStorage.setItem('chantepafo.pseudo', 'Saved')
    const { wrapper } = await mountHome()
    const inputs = wrapper.findAll('input[placeholder="Ton pseudo"]')
    expect((inputs[0].element as HTMLInputElement).value).toBe('Saved')
  })

  it('createRoom navigates to the room code on success', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).endsWith('/api/auth/register')) {
        return new Response(JSON.stringify({ token: 't', username: 'alice', user_id: 'u1' }), {
          status: 200,
        })
      }
      if (String(url).endsWith('/api/rooms')) {
        return new Response(
          JSON.stringify({ room: { code: 'FUNK4242', players: [], settings: {} } }),
          { status: 200 },
        )
      }
      return new Response('{}', { status: 404 })
    })

    const { wrapper, router } = await mountHome()
    const pushSpy = vi.spyOn(router, 'push')

    await wrapper.get('input[placeholder="Ton pseudo"]').setValue('Alice')
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()

    expect(fetchSpy).toHaveBeenCalled()
    expect(pushSpy).toHaveBeenCalledWith('/FUNK4242')
  })

  it('createRoom surfaces the FastAPI validation error when register fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [{ msg: 'Value error, Ce pseudo n’est pas autorisé', loc: ['body'] }],
        }),
        { status: 422 },
      ),
    )

    const { wrapper } = await mountHome()
    await wrapper.get('input[placeholder="Ton pseudo"]').setValue('baduser')
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Ce pseudo n’est pas autorisé')
  })

  it('createRoom surfaces a string detail error when rooms endpoint fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).endsWith('/api/auth/register')) {
        return new Response(JSON.stringify({ token: 't', username: 'alice', user_id: 'u1' }), {
          status: 200,
        })
      }
      return new Response(JSON.stringify({ detail: 'Room already exists' }), { status: 409 })
    })

    const { wrapper } = await mountHome()
    await wrapper.get('input[placeholder="Ton pseudo"]').setValue('Alice')
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Room already exists')
  })

  it('joinRoom navigates to the uppercased code on success', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).endsWith('/api/auth/register')) {
        return new Response(JSON.stringify({ token: 't', username: 'bob', user_id: 'u2' }), {
          status: 200,
        })
      }
      if (String(url).includes('/rooms/FUNK4242/join')) {
        return new Response(
          JSON.stringify({ room: { code: 'FUNK4242', players: [], settings: {} } }),
          { status: 200 },
        )
      }
      return new Response('{}', { status: 404 })
    })

    const { wrapper, router } = await mountHome()
    const pushSpy = vi.spyOn(router, 'push')

    await wrapper.get('input[placeholder="FUNK4242"]').setValue('funk4242') // lowercase
    const nameInputs = wrapper.findAll('input[placeholder="Ton pseudo"]')
    await nameInputs[1].setValue('Bob')
    await wrapper.get('button.btn-secondary').trigger('click')
    await flushPromises()

    // Normalized to uppercase
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/api/rooms/FUNK4242/join'),
      expect.any(Object),
    )
    expect(pushSpy).toHaveBeenCalledWith('/FUNK4242')
  })

  it('createRoom retries after 401 by clearing the stale token and re-registering', async () => {
    // Pre-seed a stale token in localStorage so ensureAuth short-circuits
    // and createRoom hits the 401 path on the first call to /api/rooms.
    localStorage.setItem('chantepafo_token', 'expired')
    localStorage.setItem('chantepafo_username', 'alice')
    localStorage.setItem('chantepafo_userId', 'u-old')

    let roomsCalls = 0
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).endsWith('/api/auth/register')) {
        return new Response(
          JSON.stringify({ token: 'fresh', username: 'alice', user_id: 'u-new' }),
          { status: 200 },
        )
      }
      if (String(url).endsWith('/api/rooms')) {
        roomsCalls++
        if (roomsCalls === 1) return new Response('{}', { status: 401 })
        return new Response(
          JSON.stringify({ room: { code: 'FUNK4242', players: [], settings: {} } }),
          { status: 200 },
        )
      }
      return new Response('{}', { status: 404 })
    })

    const { wrapper, router } = await mountHome()
    const pushSpy = vi.spyOn(router, 'push')

    await wrapper.get('input[placeholder="Ton pseudo"]').setValue('Alice')
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()

    // First /api/rooms was 401, we cleared auth, called /api/auth/register,
    // then retried /api/rooms successfully.
    expect(roomsCalls).toBe(2)
    const registerCalls = fetchSpy.mock.calls.filter((c) =>
      String(c[0]).endsWith('/api/auth/register'),
    )
    expect(registerCalls).toHaveLength(1)
    expect(pushSpy).toHaveBeenCalledWith('/FUNK4242')
  })

  it('joinRoom displays a fallback error when the server response is not JSON', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).endsWith('/api/auth/register')) {
        return new Response(JSON.stringify({ token: 't', username: 'bob', user_id: 'u2' }), {
          status: 200,
        })
      }
      return new Response('plain text error', { status: 500 })
    })

    const { wrapper } = await mountHome()
    await wrapper.get('input[placeholder="FUNK4242"]').setValue('ROCK0001')
    const nameInputs = wrapper.findAll('input[placeholder="Ton pseudo"]')
    await nameInputs[1].setValue('Bob')
    await wrapper.get('button.btn-secondary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Room introuvable ou pleine')
  })

  it('joinRoom requires both code and name before enabling the button', async () => {
    const { wrapper } = await mountHome()
    const joinBtn = wrapper.get('button.btn-secondary')
    expect(joinBtn.attributes('disabled')).toBeDefined()

    await wrapper.get('input[placeholder="FUNK4242"]').setValue('ROCK0001')
    expect(joinBtn.attributes('disabled')).toBeDefined() // still missing name

    const nameInputs = wrapper.findAll('input[placeholder="Ton pseudo"]')
    await nameInputs[1].setValue('Bob')
    expect(joinBtn.attributes('disabled')).toBeUndefined()
  })
})

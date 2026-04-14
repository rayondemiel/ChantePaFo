import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import GameView from '../../src/views/GameView.vue'
import { useAuthStore } from '../../src/stores/auth'
import { useGameStore } from '../../src/stores/game'

const socketMock = {
  connect: vi.fn(),
  emit: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  disconnect: vi.fn(),
}
vi.mock('../../src/composables/useSocket', () => ({
  useSocket: () => socketMock,
}))

// Give jsdom a minimal matchMedia before any component that uses
// useBreakpoint (provided in App.vue normally) mounts.

async function mountGame() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/:code/play', component: GameView, props: true },
    ],
  })
  await router.push('/FUNK4242/play')
  await router.isReady()
  const wrapper = mount(GameView, {
    props: { code: 'FUNK4242' },
    global: { plugins: [router, createPinia()] },
  })
  return { wrapper, router }
}

describe('GameView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    Object.values(socketMock).forEach((m) => m.mockReset())
  })

  it('redirects to / when there is no auth token', async () => {
    const { router } = await mountGame()
    const pushSpy = vi.spyOn(router, 'replace')
    // Re-mount fresh without token (after clearing state)
    const wrapper = mount(GameView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [router, createPinia()] },
    })
    await wrapper.vm.$nextTick()
    // The onMounted in the second mount triggers the redirect
    expect(pushSpy).toHaveBeenCalledWith('/')
  })

  it('connects the socket and registers listeners when authenticated', async () => {
    setActivePinia(createPinia())
    const authPinia = createPinia()
    setActivePinia(authPinia)
    const auth = useAuthStore()
    auth.setAuth({ token: 'tkn', username: 'alice', user_id: 'u1' })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div>home</div>' } },
        { path: '/:code/play', component: GameView, props: true },
      ],
    })
    await router.push('/FUNK4242/play')
    await router.isReady()

    mount(GameView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [router, authPinia] },
    })

    expect(socketMock.connect).toHaveBeenCalledWith('tkn')
    const events = socketMock.on.mock.calls.map((c) => c[0])
    expect(events).toContain('game_state')
    expect(events).toContain('game_ended')
    expect(events).toContain('ambiance_update')
  })

  it('hides the VolumeControl during the countdown phase', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.setAuth({ token: 't', username: 'a', user_id: 'u' })
    const gameStore = useGameStore()
    gameStore.setState({
      phase: 'countdown',
      current_round: 0,
      total_rounds: 5,
      total_scores: {},
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:code/play', component: GameView, props: true }],
    })
    await router.push('/FUNK4242/play')
    await router.isReady()
    const wrapper = mount(GameView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [router, pinia] },
    })
    expect(wrapper.find('.zone-info .volume-control').exists()).toBe(false)
  })

  it('shows the VolumeControl in the zone-info header when not in countdown', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.setAuth({ token: 't', username: 'a', user_id: 'u' })
    const gameStore = useGameStore()
    gameStore.setState({
      phase: 'playing',
      current_round: 0,
      total_rounds: 5,
      total_scores: {},
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:code/play', component: GameView, props: true }],
    })
    await router.push('/FUNK4242/play')
    await router.isReady()
    const wrapper = mount(GameView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [router, pinia] },
    })
    expect(wrapper.find('.zone-info .volume-control').exists()).toBe(true)
  })

  it('renders the translated phase name from the game store', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.setAuth({ token: 't', username: 'a', user_id: 'u' })
    const gameStore = useGameStore()
    gameStore.setState({
      phase: 'countdown',
      current_round: 0,
      total_rounds: 5,
      total_scores: {},
    })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:code/play', component: GameView, props: true }],
    })
    await router.push('/FUNK4242/play')
    await router.isReady()

    const wrapper = mount(GameView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [router, pinia] },
    })
    expect(wrapper.text()).toContain('Prêt ?')
  })

  it('game_state socket event updates the game store', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.setAuth({ token: 't', username: 'a', user_id: 'u' })
    const gameStore = useGameStore()

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:code/play', component: GameView, props: true }],
    })
    await router.push('/FUNK4242/play')
    await router.isReady()
    mount(GameView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [router, pinia] },
    })

    // Grab the handler that GameView registered for game_state
    const gameStateCall = socketMock.on.mock.calls.find((c) => c[0] === 'game_state')
    const handler = gameStateCall![1] as (data: unknown) => void
    handler({ phase: 'playing', current_round: 2, total_rounds: 10, total_scores: {} })
    expect(gameStore.state?.phase).toBe('playing')
  })

  it('unregisters socket listeners on unmount', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.setAuth({ token: 't', username: 'a', user_id: 'u' })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:code/play', component: GameView, props: true }],
    })
    await router.push('/FUNK4242/play')
    await router.isReady()
    const wrapper = mount(GameView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [router, pinia] },
    })
    wrapper.unmount()
    const offEvents = socketMock.off.mock.calls.map((c) => c[0])
    expect(offEvents).toContain('game_state')
    expect(offEvents).toContain('game_ended')
    expect(offEvents).toContain('ambiance_update')
  })
})

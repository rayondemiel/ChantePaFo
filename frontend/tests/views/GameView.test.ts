import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import GameView from '../../src/views/GameView.vue'
import { useAuthStore } from '../../src/stores/auth'
import { useGameStore } from '../../src/stores/game'
import { useRoomStore } from '../../src/stores/room'

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

async function mountGame(opts?: { authenticated?: boolean; withRoom?: boolean }) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (opts?.authenticated) {
    const auth = useAuthStore()
    auth.setAuth({ token: 't', username: 'alice', user_id: 'u1' })
  }
  if (opts?.withRoom) {
    const room = useRoomStore()
    room.setRoom({
      code: 'FUNK4242',
      players: [
        { id: 'u1', name: 'Alice', is_host: true },
        { id: 'u2', name: 'Bob', is_host: false },
      ],
      settings: {
        game_mode: 'blindtest',
        genres: { all: 2 },
        num_rounds: 5,
        extract_duration: 30,
        karaoke_variant: 'classic',
      },
      status: 'playing',
    })
  }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/:code', component: { template: '<div>lobby</div>' } },
      { path: '/:code/play', component: GameView, props: true },
    ],
  })
  await router.push('/FUNK4242/play')
  await router.isReady()
  const wrapper = mount(GameView, {
    props: { code: 'FUNK4242' },
    global: { plugins: [router, pinia] },
  })
  return { wrapper, router, pinia }
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
    const wrapper = mount(GameView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [router, createPinia()] },
    })
    await wrapper.vm.$nextTick()
    expect(pushSpy).toHaveBeenCalledWith('/')
  })

  it('connects the socket and registers listeners when authenticated', async () => {
    await mountGame({ authenticated: true })
    expect(socketMock.connect).toHaveBeenCalledWith('t')
    const events = socketMock.on.mock.calls.map((c) => c[0])
    expect(events).toContain('game_state')
    expect(events).toContain('game_ended')
    expect(events).toContain('ambiance_update')
    expect(events).toContain('left_game')
    expect(events).toContain('returned_to_lobby')
  })

  it('hides the VolumeControl during the countdown phase', async () => {
    const { pinia } = await mountGame({ authenticated: true })
    setActivePinia(pinia)
    const gameStore = useGameStore()
    gameStore.setState({ phase: 'countdown', current_round: 0, total_rounds: 5, total_scores: {} })

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
    const { pinia } = await mountGame({ authenticated: true })
    setActivePinia(pinia)
    const gameStore = useGameStore()
    gameStore.setState({ phase: 'playing', current_round: 0, total_rounds: 5, total_scores: {} })

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
    const { pinia } = await mountGame({ authenticated: true })
    setActivePinia(pinia)
    const gameStore = useGameStore()
    gameStore.setState({ phase: 'countdown', current_round: 0, total_rounds: 5, total_scores: {} })

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
    const { pinia } = await mountGame({ authenticated: true })
    setActivePinia(pinia)
    const gameStore = useGameStore()

    const gameStateCall = socketMock.on.mock.calls.find((c) => c[0] === 'game_state')
    const handler = gameStateCall![1] as (data: unknown) => void
    handler({ phase: 'playing', current_round: 2, total_rounds: 10, total_scores: {} })
    expect(gameStore.state?.phase).toBe('playing')
  })

  it('unregisters socket listeners on unmount', async () => {
    const { wrapper } = await mountGame({ authenticated: true })
    wrapper.unmount()
    const offEvents = socketMock.off.mock.calls.map((c) => c[0])
    expect(offEvents).toContain('game_state')
    expect(offEvents).toContain('game_ended')
    expect(offEvents).toContain('ambiance_update')
    expect(offEvents).toContain('left_game')
    expect(offEvents).toContain('returned_to_lobby')
  })

  it('renders quit button when game state exists', async () => {
    const { pinia } = await mountGame({ authenticated: true })
    setActivePinia(pinia)
    const gameStore = useGameStore()
    gameStore.setState({ phase: 'playing', current_round: 0, total_rounds: 5, total_scores: {} })

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
      global: { plugins: [router, pinia] },
    })
    expect(wrapper.find('[data-test="quit-game"]').exists()).toBe(true)
  })

  it('quit button opens confirm dialog', async () => {
    const { pinia } = await mountGame({ authenticated: true, withRoom: true })
    setActivePinia(pinia)
    const gameStore = useGameStore()
    gameStore.setState({ phase: 'playing', current_round: 0, total_rounds: 5, total_scores: {} })

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
      global: { plugins: [router, pinia] },
    })
    await wrapper.find('[data-test="quit-game"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Quitter la partie ?')
  })

  it('left_game event navigates to home', async () => {
    const { router } = await mountGame({ authenticated: true })
    const pushSpy = vi.spyOn(router, 'push')

    const leftGameCall = socketMock.on.mock.calls.find((c) => c[0] === 'left_game')
    const handler = leftGameCall![1] as () => void
    handler()
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledWith('/')
  })

  it('returned_to_lobby event navigates to lobby', async () => {
    const { router } = await mountGame({ authenticated: true })
    const pushSpy = vi.spyOn(router, 'push')

    const returnedCall = socketMock.on.mock.calls.find((c) => c[0] === 'returned_to_lobby')
    const handler = returnedCall![1] as (data: unknown) => void
    handler({ code: 'FUNK4242' })
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledWith('/FUNK4242')
  })
})

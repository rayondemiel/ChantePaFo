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

const ambianceMock = {
  start: vi.fn(),
  stop: vi.fn(),
  connectAudio: vi.fn(),
}
vi.mock('../../src/composables/useAmbiance', () => ({
  useAmbiance: () => ambianceMock,
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
    Object.values(ambianceMock).forEach((m) => m.mockReset())
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
    // ambiance_update is now registered in App.vue (always-on, survives nav).
    // GameView no longer subscribes to it — see App.vue's onMounted comment.
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

  it.each([
    ['playing_reveal', 'Révélation'],
    ['round_pause', 'Manche suivante'],
  ])('translates the blindtest %s phase instead of showing the raw id', async (phase, label) => {
    const { pinia } = await mountGame({ authenticated: true })
    setActivePinia(pinia)
    const gameStore = useGameStore()
    gameStore.setState({ phase, current_round: 0, total_rounds: 5, total_scores: {} })

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
    expect(wrapper.find('.zone-info-main').text()).toContain(label)
    expect(wrapper.find('.zone-info-main').text()).not.toContain(phase)
  })

  it('re-enters the socket room and reloads the room on mount (page reload mid-game)', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          room: {
            code: 'FUNK4242',
            players: [{ id: 'u1', name: 'Alice', is_host: true }],
            settings: {
              game_mode: 'blindtest',
              genres: { all: 2 },
              num_rounds: 5,
              extract_duration: 30,
              karaoke_variant: 'classic',
            },
            status: 'playing',
          },
        }),
        { status: 200 },
      ),
    )
    const { pinia } = await mountGame({ authenticated: true })
    await flushPromises()
    setActivePinia(pinia)
    expect(socketMock.emit).toHaveBeenCalledWith('join_room', { code: 'FUNK4242' })
    expect(fetchSpy).toHaveBeenCalledWith('/api/rooms/FUNK4242', expect.anything())
    expect(useRoomStore().room?.code).toBe('FUNK4242')
    fetchSpy.mockRestore()
  })

  it('sends the player back to the lobby when the room is no longer playing', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          room: {
            code: 'FUNK4242',
            players: [{ id: 'u1', name: 'Alice', is_host: true }],
            settings: {
              game_mode: 'blindtest',
              genres: { all: 2 },
              num_rounds: 5,
              extract_duration: 30,
              karaoke_variant: 'classic',
            },
            status: 'lobby',
          },
        }),
        { status: 200 },
      ),
    )
    const { router } = await mountGame({ authenticated: true })
    const replaceSpy = vi.spyOn(router, 'replace')
    await flushPromises()
    expect(replaceSpy).toHaveBeenCalledWith('/FUNK4242')
    fetchSpy.mockRestore()
  })

  it('sends the player home when the room does not exist any more', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(JSON.stringify({ detail: 'nope' }), { status: 404 }))
    const { router } = await mountGame({ authenticated: true })
    const replaceSpy = vi.spyOn(router, 'replace')
    await flushPromises()
    expect(replaceSpy).toHaveBeenCalledWith('/')
    fetchSpy.mockRestore()
  })

  it('room_updated socket event refreshes the roster (host handover mid-game)', async () => {
    const { pinia } = await mountGame({ authenticated: true, withRoom: true })
    setActivePinia(pinia)
    const roomStore = useRoomStore()
    expect(roomStore.isHost).toBe(true)
    const handler = socketMock.on.mock.calls.find((c) => c[0] === 'room_updated')?.[1]
    expect(handler).toBeDefined()
    handler!({
      code: 'FUNK4242',
      players: [{ id: 'u2', name: 'Bob', is_host: true }],
      settings: roomStore.room!.settings,
      status: 'playing',
    })
    expect(roomStore.isHost).toBe(false)
    expect(roomStore.room!.players.map((p) => p.name)).toEqual(['Bob'])
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

  it('starts the ambiance loop on mount when authenticated', async () => {
    await mountGame({ authenticated: true })
    expect(ambianceMock.start).toHaveBeenCalledTimes(1)
  })

  it('stops the ambiance loop on unmount', async () => {
    const { wrapper } = await mountGame({ authenticated: true })
    expect(ambianceMock.stop).not.toHaveBeenCalled()
    wrapper.unmount()
    expect(ambianceMock.stop).toHaveBeenCalledTimes(1)
  })

  it('unregisters socket listeners on unmount', async () => {
    const { wrapper } = await mountGame({ authenticated: true })
    wrapper.unmount()
    const offEvents = socketMock.off.mock.calls.map((c) => c[0])
    expect(offEvents).toContain('game_state')
    expect(offEvents).toContain('game_ended')
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

  it('renders the reaction bar and soundboard during gameplay', async () => {
    const { pinia } = await mountGame({ authenticated: true, withRoom: true })
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
    const social = wrapper.find('.zone-social')
    expect(social.exists()).toBe(true)
    expect(social.classes()).not.toContain('zone-social--hidden')
    expect(social.find('.reaction-bar').exists()).toBe(true)
    expect(social.find('.soundboard').exists()).toBe(true)
  })

  it('keeps the social zone mounted but visually hidden during countdown', async () => {
    const { pinia } = await mountGame({ authenticated: true, withRoom: true })
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
    // Mounted (so reaction listeners stay alive) but opacity-hidden — a v-if
    // here would unmount the sockets listeners and reflow the whole page.
    const social = wrapper.get('.zone-social')
    expect(social.classes()).toContain('zone-social--hidden')
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

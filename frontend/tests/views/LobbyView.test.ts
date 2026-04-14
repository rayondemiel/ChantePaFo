/* eslint-disable security/detect-object-injection -- test uses controlled event keys */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import LobbyView from '../../src/views/LobbyView.vue'
import { useAuthStore } from '../../src/stores/auth'
import { useRoomStore } from '../../src/stores/room'
import type { RoomState } from '../../src/types'

type SocketHandler = (...args: unknown[]) => void
const socketHandlers: Record<string, SocketHandler[]> = {}
const socketMock = {
  connect: vi.fn(),
  emit: vi.fn(),
  on: vi.fn((event: string, handler: SocketHandler) => {
    ;(socketHandlers[event] ??= []).push(handler)
  }),
  off: vi.fn(),
  disconnect: vi.fn(),
}
function fireSocket(event: string, data: unknown) {
  for (const h of socketHandlers[event] ?? []) h(data)
}

vi.mock('../../src/composables/useSocket', () => ({
  useSocket: () => socketMock,
}))

const clipboardWriteText = vi.fn().mockResolvedValue(undefined)
Object.defineProperty(navigator, 'clipboard', {
  value: { writeText: clipboardWriteText },
  writable: true,
  configurable: true,
})

const baseRoom: RoomState = {
  code: 'FUNK4242',
  // host_id is a backend field not exposed via public_room, but kept here
  // for the pinia setRoom signature used by the room store in tests.
  players: [
    { id: 'u1', name: 'Alice', is_host: true },
    { id: 'u2', name: 'Bob', is_host: false },
  ],
  settings: {
    game_mode: 'blindtest',
    genres: { pop: 2, rock: 3 },
    num_rounds: 10,
    extract_duration: 20,
    karaoke_variant: 'classic',
  },
  status: 'lobby',
}

async function mountLobby(opts?: { asHost?: boolean; noToken?: boolean; room?: RoomState }) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  if (!opts?.noToken) {
    auth.setAuth({
      token: 't',
      username: opts?.asHost === false ? 'bob' : 'alice',
      user_id: opts?.asHost === false ? 'u2' : 'u1',
    })
  }
  const roomStore = useRoomStore()
  roomStore.setRoom(opts?.room ?? baseRoom)

  // Silence the room GET inside onMounted
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ room: opts?.room ?? baseRoom }), { status: 200 }),
  )

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/:code', component: LobbyView, props: true },
      { path: '/:code/play', component: { template: '<div>play</div>' } },
    ],
  })
  await router.push('/FUNK4242')
  await router.isReady()

  const wrapper = mount(LobbyView, {
    props: { code: 'FUNK4242' },
    global: { plugins: [router, pinia] },
  })
  await flushPromises()
  return { wrapper, router, pinia, auth, roomStore }
}

describe('LobbyView', () => {
  let wrapper: VueWrapper | null = null
  let router: Router | null = null

  beforeEach(() => {
    Object.keys(socketHandlers).forEach((k) => delete socketHandlers[k])
    Object.values(socketMock).forEach((m) => m.mockReset())
    socketMock.on.mockImplementation((event: string, handler: SocketHandler) => {
      ;(socketHandlers[event] ??= []).push(handler)
    })
    clipboardWriteText.mockReset().mockResolvedValue(undefined)
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    wrapper?.unmount()
    wrapper = null
    router = null
  })

  it('redirects to / when there is no auth token', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const localRouter = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div>home</div>' } },
        { path: '/:code', component: LobbyView, props: true },
      ],
    })
    await localRouter.push('/FUNK4242')
    await localRouter.isReady()
    const replaceSpy = vi.spyOn(localRouter, 'replace')
    mount(LobbyView, {
      props: { code: 'FUNK4242' },
      global: { plugins: [localRouter, pinia] },
    })
    await flushPromises()
    expect(replaceSpy).toHaveBeenCalledWith('/')
  })

  it('connects the socket and emits join_room on mount', async () => {
    ;({ wrapper, router } = await mountLobby())
    expect(socketMock.connect).toHaveBeenCalledWith('t')
    expect(socketMock.emit).toHaveBeenCalledWith('join_room', { code: 'FUNK4242' })
  })

  it('renders the VolumeControl in the header', async () => {
    ;({ wrapper, router } = await mountLobby())
    expect(wrapper!.find('.volume-control').exists()).toBe(true)
  })

  it('renders the marquee code, host name and player count', async () => {
    ;({ wrapper, router } = await mountLobby())
    expect(wrapper!.text()).toContain('FUNK4242')
    expect(wrapper!.text()).toContain('Alice')
    expect(wrapper!.text()).toContain('2/10 joueurs')
  })

  it('shows the console panel when the user is host', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    expect(wrapper!.find('.panel-console').exists()).toBe(true)
    expect(wrapper!.find('.panel-waiting').exists()).toBe(false)
  })

  it('shows the waiting panel with live server settings for spectators', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: false }))
    expect(wrapper!.find('.panel-waiting').exists()).toBe(true)
    expect(wrapper!.find('.panel-console').exists()).toBe(false)
    // Readout row shows the mode label from room.settings
    expect(wrapper!.text()).toContain('Blindtest')
    expect(wrapper!.text()).toContain('10')
  })

  it('setMode click emits update_settings with the new mode', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    socketMock.emit.mockClear()
    await wrapper!.get('.mode-card.mode-karaoke').trigger('click')
    const call = socketMock.emit.mock.calls.find((c) => c[0] === 'update_settings')
    expect(call).toBeDefined()
    expect((call![1] as { settings: { game_mode: string } }).settings.game_mode).toBe('karaoke')
  })

  it('setNumRounds click emits update_settings with the new round count', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    socketMock.emit.mockClear()
    // Pick the "5" seg button from the Manches group (first .seg-group-tight)
    const segs = wrapper!.findAll('.seg-group-tight .seg')
    await segs[1].trigger('click')
    const call = socketMock.emit.mock.calls.find((c) => c[0] === 'update_settings')
    expect(call).toBeDefined()
    expect((call![1] as { settings: { num_rounds: number } }).settings.num_rounds).toBe(5)
  })

  it('copyCode writes the room code to the clipboard and shows a toast', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    await wrapper!.get('.marquee-code').trigger('click')
    await flushPromises()
    expect(clipboardWriteText).toHaveBeenCalledWith('FUNK4242')
    expect(wrapper!.text()).toContain('Code copié')
  })

  it('clicking the Quitter chip opens the leave confirmation dialog', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    const leaveChip = wrapper!.findAll('.chip').find((b) => b.text().includes('Quitter'))
    await leaveChip!.trigger('click')
    expect(wrapper!.text()).toContain('Quitter la room')
  })

  it('confirms leaveRoom disconnects the socket and navigates home', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    const leaveChip = wrapper!.findAll('.chip').find((b) => b.text().includes('Quitter'))
    await leaveChip!.trigger('click')
    // Click the danger button inside the dialog
    const danger = wrapper!.findAll('.btn-danger').at(-1)
    const pushSpy = vi.spyOn(router!, 'push')
    await danger!.trigger('click')
    await flushPromises()
    expect(socketMock.disconnect).toHaveBeenCalled()
    expect(pushSpy).toHaveBeenCalledWith('/')
  })

  it('kickPlayer opens the kick confirmation with the target name', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    // PlayerList renders a btn-kick only for non-host players — Bob has one.
    const kickBtn = wrapper!.get('.btn-kick')
    await kickBtn.trigger('click')
    expect(wrapper!.text()).toContain('Exclure Bob')
  })

  it('confirming the kick emits kick_player with the target id', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    await wrapper!.get('.btn-kick').trigger('click')
    socketMock.emit.mockClear()
    // Find the confirm dialog danger button inside the kick modal
    const danger = wrapper!.findAll('.btn-danger').at(-1)
    await danger!.trigger('click')
    expect(socketMock.emit).toHaveBeenCalledWith('kick_player', {
      code: 'FUNK4242',
      player_id: 'u2',
    })
  })

  it('onPlayerKicked opens the kicked notice dialog when the target is the current user', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: false }))
    fireSocket('player_kicked', { player_id: 'u2' })
    await flushPromises()
    expect(wrapper!.text()).toContain('Tu as été exclu')
  })

  it('onPlayerKicked ignores events targeting other players', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: false }))
    fireSocket('player_kicked', { player_id: 'someone-else' })
    await flushPromises()
    expect(wrapper!.text()).not.toContain('Tu as été exclu')
  })

  it('onError displays the server error message', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    fireSocket('error', { message: 'Nope, pas autorisé' })
    await flushPromises()
    expect(wrapper!.text()).toContain('Nope, pas autorisé')
  })

  it('onGameState navigates to /:code/play', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    const pushSpy = vi.spyOn(router!, 'push')
    fireSocket('game_state', {
      phase: 'countdown',
      current_round: 0,
      total_rounds: 10,
      total_scores: {},
    })
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledWith('/FUNK4242/play')
  })

  it('startGame click emits start_game', async () => {
    const fullRoom: RoomState = {
      ...baseRoom,
      players: [
        { id: 'u1', name: 'Alice', is_host: true },
        { id: 'u2', name: 'Bob', is_host: false },
      ],
    }
    ;({ wrapper, router } = await mountLobby({ asHost: true, room: fullRoom }))
    socketMock.emit.mockClear()
    await wrapper!.get('.btn-launch').trigger('click')
    expect(socketMock.emit).toHaveBeenCalledWith('start_game', { code: 'FUNK4242' })
  })

  it('onGenresUpdate emits update_settings when GenreSelector fires update', async () => {
    ;({ wrapper, router } = await mountLobby({ asHost: true }))
    socketMock.emit.mockClear()
    // GenreSelector is rendered inside the console — directly toggle a chip
    const chip = wrapper!.findAll('.chip-electro').at(0)
    await chip!.trigger('click')
    const call = socketMock.emit.mock.calls.find((c) => c[0] === 'update_settings')
    expect(call).toBeDefined()
  })
})

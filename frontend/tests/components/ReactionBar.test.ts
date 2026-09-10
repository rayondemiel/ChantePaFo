import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import ReactionBar from '../../src/components/ReactionBar.vue'
import { useRoomStore } from '../../src/stores/room'
import { useGameStore } from '../../src/stores/game'
import { getPlayerHue } from '../../src/lib/playerHue'

const socketMock = {
  connect: vi.fn(),
  emit: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  disconnect: vi.fn(),
  connected: { value: true },
  getSocket: vi.fn(),
}
vi.mock('../../src/composables/useSocket', () => ({
  useSocket: () => socketMock,
}))

function setupRoom(code = 'FUNK4242') {
  const room = useRoomStore()
  room.setRoom({
    code,
    players: [
      { id: 'u1', name: 'Alice', is_host: true },
      { id: 'u2', name: 'Bob', is_host: false },
    ],
    settings: {
      game_mode: 'blindtest',
      genres: { all: 1 },
      num_rounds: 10,
      extract_duration: 20,
      karaoke_variant: 'classic',
    },
    status: 'playing',
  })
}

function receivedHandler(): (data: unknown) => void {
  const call = socketMock.on.mock.calls.find((c) => c[0] === 'reaction_received')
  expect(call).toBeDefined()
  return call![1] as (data: unknown) => void
}

describe('ReactionBar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    socketMock.emit.mockReset()
    socketMock.on.mockReset()
    socketMock.off.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the six reaction emojis as round buttons', () => {
    setupRoom()
    const wrapper = mount(ReactionBar)
    const buttons = wrapper.findAll('.react-btn')
    expect(buttons).toHaveLength(6)
    expect(buttons.map((b) => b.text())).toEqual(['😂', '👏', '💀', '🔥', '😱', '❤️'])
  })

  it('emits reaction with exactly code and emoji (strict backend payload)', async () => {
    setupRoom()
    const wrapper = mount(ReactionBar)
    await wrapper.findAll('.react-btn')[3].trigger('click')

    expect(socketMock.emit).toHaveBeenCalledOnce()
    const [event, payload] = socketMock.emit.mock.calls[0]
    expect(event).toBe('reaction')
    expect(payload).toEqual({ code: 'FUNK4242', emoji: '🔥' })
    // extra="forbid" server-side: any additional key gets the event rejected.
    expect(Object.keys(payload as object).sort()).toEqual(['code', 'emoji'])
  })

  it('does not emit without a room', async () => {
    const wrapper = mount(ReactionBar)
    await wrapper.findAll('.react-btn')[0].trigger('click')
    expect(socketMock.emit).not.toHaveBeenCalled()
  })

  it('floats the emoji with the sender name when reaction_received fires', async () => {
    setupRoom()
    const wrapper = mount(ReactionBar)

    receivedHandler()({ player_id: 'u2', player_name: 'Bob', emoji: '💀' })
    await nextTick()

    const floating = wrapper.find('.floating')
    expect(floating.exists()).toBe(true)
    expect(floating.text()).toContain('💀')
    expect(floating.text()).toContain('Bob')
  })

  it('removes the floating emoji after its animation window', async () => {
    vi.useFakeTimers()
    setupRoom()
    const wrapper = mount(ReactionBar)

    receivedHandler()({ player_id: 'u2', player_name: 'Bob', emoji: '👏' })
    await nextTick()
    expect(wrapper.find('.floating').exists()).toBe(true)

    vi.advanceTimersByTime(2000)
    await nextTick()
    expect(wrapper.find('.floating').exists()).toBe(false)
  })

  it('stacks simultaneous reactions from several players', async () => {
    setupRoom()
    const wrapper = mount(ReactionBar)
    const handler = receivedHandler()

    handler({ player_id: 'u1', player_name: 'Alice', emoji: '😂' })
    handler({ player_id: 'u2', player_name: 'Bob', emoji: '🔥' })
    await nextTick()

    expect(wrapper.findAll('.floating')).toHaveLength(2)
  })

  it('tints the float with the sender hue', async () => {
    setupRoom()
    const wrapper = mount(ReactionBar)

    receivedHandler()({ player_id: 'u2', player_name: 'Bob', emoji: '🔥' })
    await nextTick()

    const style = wrapper.get('.floating').attributes('style') ?? ''
    expect(style).toContain(`--hue: ${getPlayerHue('u2')}`)
  })

  it('confines floats to the side gutters while the round is playing', async () => {
    setupRoom()
    const game = useGameStore()
    game.setState({ phase: 'playing', current_round: 0, total_rounds: 5, total_scores: {} })
    const wrapper = mount(ReactionBar)
    const handler = receivedHandler()

    for (let i = 0; i < 12; i++) {
      handler({ player_id: 'u2', player_name: 'Bob', emoji: '🔥' })
    }
    await nextTick()

    const floats = wrapper.findAll('.floating')
    expect(floats.length).toBeGreaterThan(0)
    for (const f of floats) {
      const left = parseFloat(/left: ([\d.]+)%/.exec(f.attributes('style') ?? '')?.[1] ?? 'NaN')
      expect(Number.isNaN(left)).toBe(false)
      const inGutter = (left >= 4 && left <= 16) || (left >= 84 && left <= 96)
      expect(inGutter).toBe(true)
    }
  })

  it('caps concurrent floats at 12, culling the oldest', async () => {
    setupRoom()
    const wrapper = mount(ReactionBar)
    const handler = receivedHandler()

    for (let i = 0; i < 15; i++) {
      handler({ player_id: 'u2', player_name: 'Bob', emoji: '👏' })
    }
    await nextTick()

    expect(wrapper.findAll('.floating')).toHaveLength(12)
  })

  it('unregisters the reaction_received handler on unmount', () => {
    setupRoom()
    const wrapper = mount(ReactionBar)
    const handler = receivedHandler()

    wrapper.unmount()

    const offCall = socketMock.off.mock.calls.find((c) => c[0] === 'reaction_received')
    expect(offCall).toBeDefined()
    expect(offCall![1]).toBe(handler)
  })
})

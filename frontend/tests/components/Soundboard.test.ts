import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import Soundboard from '../../src/components/Soundboard.vue'
import { useRoomStore } from '../../src/stores/room'

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

// jsdom's Audio can't play anything — install a controllable fake.
class FakeAudio {
  static instances: FakeAudio[] = []
  static playShouldReject = false
  src: string
  currentTime = 0
  play = vi.fn(() =>
    FakeAudio.playShouldReject ? Promise.reject(new Error('NotSupportedError')) : Promise.resolve(),
  )
  constructor(src: string) {
    this.src = src
    FakeAudio.instances.push(this)
  }
}

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

function playedHandler(): (data: unknown) => void {
  const call = socketMock.on.mock.calls.find((c) => c[0] === 'soundboard_played')
  expect(call).toBeDefined()
  return call![1] as (data: unknown) => void
}

describe('Soundboard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    socketMock.emit.mockReset()
    socketMock.on.mockReset()
    socketMock.off.mockReset()
    FakeAudio.instances = []
    FakeAudio.playShouldReject = false
    vi.stubGlobal('Audio', FakeAudio)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('renders the five allowed sounds', () => {
    setupRoom()
    const wrapper = mount(Soundboard)
    expect(wrapper.findAll('.sound-btn')).toHaveLength(5)
  })

  it('emits soundboard with exactly code and sound, without playing locally', async () => {
    setupRoom()
    const wrapper = mount(Soundboard)
    await wrapper.get('[data-test="sound-drumroll"]').trigger('click')

    expect(socketMock.emit).toHaveBeenCalledOnce()
    const [event, payload] = socketMock.emit.mock.calls[0]
    expect(event).toBe('soundboard')
    expect(payload).toEqual({ code: 'FUNK4242', sound: 'drumroll' })
    expect(Object.keys(payload as object).sort()).toEqual(['code', 'sound'])
    // Playback happens on the soundboard_played echo so everyone stays in sync.
    expect(FakeAudio.instances).toHaveLength(0)
  })

  it('does not emit without a room', async () => {
    const wrapper = mount(Soundboard)
    await wrapper.get('[data-test="sound-applause"]').trigger('click')
    expect(socketMock.emit).not.toHaveBeenCalled()
  })

  it('plays the matching file when soundboard_played is received', async () => {
    setupRoom()
    mount(Soundboard)

    playedHandler()({ player_name: 'Bob', sound: 'airhorn' })
    await flushPromises()

    expect(FakeAudio.instances).toHaveLength(1)
    expect(FakeAudio.instances[0].src).toBe('/sounds/airhorn.mp3')
    expect(FakeAudio.instances[0].play).toHaveBeenCalledOnce()
  })

  it('survives a missing sound file (play rejection is swallowed)', async () => {
    setupRoom()
    FakeAudio.playShouldReject = true
    mount(Soundboard)

    playedHandler()({ player_name: 'Bob', sound: 'boo' })
    await flushPromises()

    expect(FakeAudio.instances[0].play).toHaveBeenCalledOnce()
  })

  it('shows an attributed event capsule (hue, name, sound) and glows the matching button', async () => {
    setupRoom()
    const wrapper = mount(Soundboard)

    playedHandler()({ player_id: 'u2', player_name: 'Bob', sound: 'drumroll' })
    await nextTick()

    const capsule = wrapper.get('[data-test="event-capsule"]')
    expect(capsule.classes()).toContain('event-capsule--visible')
    expect(capsule.text()).toContain('Bob')
    expect(capsule.text()).toContain('🥁')
    expect(capsule.text()).toContain('Roulement')
    expect(capsule.attributes('style')).toContain('--hue')
    expect(wrapper.get('[data-test="sound-drumroll"]').classes()).toContain('sound-btn-glow')
  })

  it('keeps the capsule mounted for aria-live and hides it after its display window', async () => {
    vi.useFakeTimers()
    setupRoom()
    const wrapper = mount(Soundboard)
    const capsule = wrapper.get('[data-test="event-capsule"]')
    expect(capsule.classes()).not.toContain('event-capsule--visible')

    playedHandler()({ player_id: 'u2', player_name: 'Bob', sound: 'boo' })
    await nextTick()
    expect(capsule.classes()).toContain('event-capsule--visible')

    vi.advanceTimersByTime(1600)
    await nextTick()
    expect(capsule.classes()).not.toContain('event-capsule--visible')
  })

  it('recharges only the pressed chip, keeping the rest of the board alive', async () => {
    setupRoom()
    const wrapper = mount(Soundboard)
    await wrapper.get('[data-test="sound-applause"]').trigger('click')

    const pressed = wrapper.get('[data-test="sound-applause"]')
    expect(pressed.classes()).toContain('sound-btn-recharging')
    expect(pressed.attributes('aria-disabled')).toBe('true')
    const other = wrapper.get('[data-test="sound-boo"]')
    expect(other.attributes('disabled')).toBeUndefined()
    expect(other.classes()).not.toContain('sound-btn-recharging')
  })

  it('vibrates on received sounds when the device supports it', async () => {
    setupRoom()
    const vibrate = vi.fn()
    Object.defineProperty(navigator, 'vibrate', {
      value: vibrate,
      writable: true,
      configurable: true,
    })
    mount(Soundboard)

    playedHandler()({ player_id: 'u2', player_name: 'Bob', sound: 'airhorn' })
    await flushPromises()

    expect(vibrate).toHaveBeenCalledOnce()
  })

  it('reuses one Audio element per sound instead of allocating per play', async () => {
    setupRoom()
    mount(Soundboard)
    const handler = playedHandler()

    handler({ player_name: 'Bob', sound: 'applause' })
    await flushPromises()
    handler({ player_name: 'Alice', sound: 'applause' })
    await flushPromises()

    expect(FakeAudio.instances).toHaveLength(1)
    expect(FakeAudio.instances[0].play).toHaveBeenCalledTimes(2)
  })

  it('applies a short cooldown after sending (anti-spam)', async () => {
    vi.useFakeTimers()
    setupRoom()
    const wrapper = mount(Soundboard)

    await wrapper.get('[data-test="sound-applause"]').trigger('click')
    await wrapper.get('[data-test="sound-boo"]').trigger('click')
    expect(socketMock.emit).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1500)
    await nextTick()
    await wrapper.get('[data-test="sound-boo"]').trigger('click')
    expect(socketMock.emit).toHaveBeenCalledTimes(2)
  })

  it('unregisters the soundboard_played handler on unmount', () => {
    setupRoom()
    const wrapper = mount(Soundboard)
    const handler = playedHandler()

    wrapper.unmount()

    const offCall = socketMock.off.mock.calls.find((c) => c[0] === 'soundboard_played')
    expect(offCall).toBeDefined()
    expect(offCall![1]).toBe(handler)
  })
})

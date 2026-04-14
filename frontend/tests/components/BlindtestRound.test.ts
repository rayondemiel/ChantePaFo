import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import BlindtestRound from '../../src/components/BlindtestRound.vue'
import { useAuthStore } from '../../src/stores/auth'
import { useRoomStore } from '../../src/stores/room'
import { useGameStore } from '../../src/stores/game'
import type { GameState, FuzzyResult } from '../../src/types'

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

const attachMusicMock: ReturnType<typeof vi.fn<(el: HTMLAudioElement) => () => void>> = vi.fn(
  () => () => {},
)
vi.mock('../../src/composables/useVolume', () => ({
  useVolume: () => ({
    music: { value: 0.8 },
    musicMuted: { value: false },
    setMusic: vi.fn(),
    toggleMusicMute: vi.fn(),
    attachMusic: attachMusicMock,
  }),
}))

async function setup(state: Partial<GameState>, opts: { isHost?: boolean; userId?: string } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.setAuth({ token: 't', username: 'alice', user_id: opts.userId ?? 'u1' })
  const room = useRoomStore()
  room.setRoom({
    code: 'FUNK4242',
    players: [
      { id: 'u1', name: 'Alice', is_host: opts.isHost ?? false },
      { id: 'u2', name: 'Bob', is_host: !(opts.isHost ?? false) },
    ],
    settings: {
      game_mode: 'blindtest',
      genres: { all: 5 },
      num_rounds: 5,
      extract_duration: 30,
      karaoke_variant: 'classic',
    },
    status: 'playing',
  })
  const game = useGameStore()
  game.setState({
    phase: 'countdown',
    current_round: 0,
    total_rounds: 5,
    total_scores: { u1: 0, u2: 0 },
    ...state,
  })

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/:code', component: { template: '<div>lobby</div>' } },
      { path: '/:code/play', component: { template: '<div>play</div>' } },
    ],
  })
  await router.push('/FUNK4242/play')
  await router.isReady()
  const wrapper = mount(BlindtestRound, {
    global: { plugins: [router, pinia] },
  })
  return { wrapper, router, game }
}

describe('BlindtestRound', () => {
  beforeEach(() => {
    Object.values(socketMock).forEach((m) => {
      if (typeof m === 'function' && 'mockReset' in m) m.mockReset()
    })
    attachMusicMock.mockClear()
    attachMusicMock.mockImplementation(() => () => {})
  })

  it('renders Countdown component in countdown phase', async () => {
    const { wrapper } = await setup({ phase: 'countdown' })
    expect(wrapper.find('.countdown-digit').exists()).toBe(true)
  })

  it('emits game_event with countdown_done when Countdown finishes', async () => {
    const { wrapper } = await setup({ phase: 'countdown' })
    const countdown = wrapper.findComponent({ name: 'Countdown' })
    countdown.vm.$emit('done')
    await flushPromises()
    const call = socketMock.emit.mock.calls.find(
      (c) =>
        c[0] === 'game_event' && (c[1] as { event_type: string }).event_type === 'countdown_done',
    )
    expect(call).toBeDefined()
    expect(call![1]).toMatchObject({
      code: 'FUNK4242',
      event_type: 'countdown_done',
      payload: {},
    })
    expect(call![1]).not.toHaveProperty('player_id')
  })

  it('renders AnswerInput and audio element during playing phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    expect(wrapper.find('input.input-answer').exists()).toBe(true)
    expect(wrapper.find('audio').exists()).toBe(true)
  })

  it('renders the mystery orb during playing phase without leaking cover art', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    expect(wrapper.find('.mystery-orb').exists()).toBe(true)
    expect(wrapper.find('img').exists()).toBe(false)
  })

  it('AnswerInput is enabled during playing phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const input = wrapper.get('input.input-answer')
    expect((input.element as HTMLInputElement).disabled).toBe(false)
  })

  it('renders ScoreBoard during playing phase with compact styling', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
      total_scores: { u1: 5, u2: 3 },
    })
    const scoreboard = wrapper.findComponent({ name: 'ScoreBoard' })
    expect(scoreboard.exists()).toBe(true)
    const rows = wrapper.findAll('.score-row')
    expect(rows.length).toBe(2)
    expect(wrapper.find('.scoreboard-compact').exists()).toBe(true)
  })

  it('emits game_event with answer payload when AnswerInput submits', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const input = wrapper.get('input.input-answer')
    await input.setValue('Thriller')
    await input.trigger('keydown.enter')
    const call = socketMock.emit.mock.calls.find(
      (c) => c[0] === 'game_event' && (c[1] as { event_type: string }).event_type === 'answer',
    )
    expect(call).toBeDefined()
    const payload = call![1] as {
      code: string
      event_type: string
      payload: { text: string; time_ms: number }
    }
    expect(payload.code).toBe('FUNK4242')
    expect(payload).not.toHaveProperty('player_id')
    expect(payload.payload.text).toBe('Thriller')
    expect(typeof payload.payload.time_ms).toBe('number')
  })

  it('subscribes and unsubscribes from game_event_result', async () => {
    const { wrapper } = await setup({ phase: 'playing' })
    const subscribed = socketMock.on.mock.calls.map((c) => c[0])
    expect(subscribed).toContain('game_event_result')
    wrapper.unmount()
    const unsubscribed = socketMock.off.mock.calls.map((c) => c[0])
    expect(unsubscribed).toContain('game_event_result')
  })

  it('shows feedback when a game_event_result targets the current player', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const handlerCall = socketMock.on.mock.calls.find((c) => c[0] === 'game_event_result')
    const handler = handlerCall![1] as (d: unknown) => void
    const result: FuzzyResult & { player_id: string } = {
      player_id: 'u1',
      title_match: true,
      artist_match: true,
      bonus: true,
      distance: 0,
    }
    handler(result)
    await flushPromises()
    expect(wrapper.text()).toContain('Parfait')
  })

  it('ignores game_event_result when targeted at another player', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const handlerCall = socketMock.on.mock.calls.find((c) => c[0] === 'game_event_result')
    const handler = handlerCall![1] as (d: unknown) => void
    handler({
      player_id: 'u2',
      title_match: true,
      artist_match: true,
      bonus: true,
      distance: 0,
    })
    await flushPromises()
    expect(wrapper.text()).not.toContain('Parfait')
  })

  it('locally reveals the song on bonus match during playing phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const handlerCall = socketMock.on.mock.calls.find((c) => c[0] === 'game_event_result')
    const handler = handlerCall![1] as (d: unknown) => void
    handler({
      player_id: 'u1',
      title_match: true,
      artist_match: true,
      bonus: true,
      distance: 0,
      correct_title: 'Thriller',
      correct_artist: 'Michael Jackson',
      cover_url: 'http://c/o.jpg',
    })
    await flushPromises()

    expect(wrapper.find('.mystery-orb').exists()).toBe(false)
    expect(wrapper.text()).toContain('Thriller')
    expect(wrapper.text()).toContain('Michael Jackson')
    const img = wrapper.find('img.reveal-cover')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('http://c/o.jpg')
    const input = wrapper.get('input.input-answer')
    expect((input.element as HTMLInputElement).disabled).toBe(true)
  })

  it('does not locally reveal on a partial (non-bonus) match', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const handlerCall = socketMock.on.mock.calls.find((c) => c[0] === 'game_event_result')
    const handler = handlerCall![1] as (d: unknown) => void
    handler({
      player_id: 'u1',
      title_match: true,
      artist_match: false,
      bonus: false,
      distance: 0,
    })
    await flushPromises()

    expect(wrapper.find('.mystery-orb').exists()).toBe(true)
    expect(wrapper.find('img.reveal-cover').exists()).toBe(false)
    const input = wrapper.get('input.input-answer')
    expect((input.element as HTMLInputElement).disabled).toBe(false)
  })

  it('ignores local reveal when bonus targets another player', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const handlerCall = socketMock.on.mock.calls.find((c) => c[0] === 'game_event_result')
    const handler = handlerCall![1] as (d: unknown) => void
    handler({
      player_id: 'u2',
      title_match: true,
      artist_match: true,
      bonus: true,
      distance: 0,
      correct_title: 'Thriller',
      correct_artist: 'Michael Jackson',
      cover_url: 'http://c/o.jpg',
    })
    await flushPromises()

    expect(wrapper.find('.mystery-orb').exists()).toBe(true)
    expect(wrapper.find('img.reveal-cover').exists()).toBe(false)
  })

  it('resets local reveal state on the next round', async () => {
    const { wrapper, game } = await setup({
      phase: 'playing',
      current_round: 0,
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const handlerCall = socketMock.on.mock.calls.find((c) => c[0] === 'game_event_result')
    const handler = handlerCall![1] as (d: unknown) => void
    handler({
      player_id: 'u1',
      title_match: true,
      artist_match: true,
      bonus: true,
      distance: 0,
      correct_title: 'Thriller',
      correct_artist: 'Michael Jackson',
      cover_url: 'http://c/o.jpg',
    })
    await flushPromises()
    expect(wrapper.find('img.reveal-cover').exists()).toBe(true)

    game.setState({
      phase: 'round_pause',
      current_round: 0,
      total_rounds: 5,
      total_scores: { u1: 0, u2: 0 },
    })
    await flushPromises()

    game.setState({
      phase: 'playing',
      current_round: 1,
      total_rounds: 5,
      total_scores: { u1: 0, u2: 0 },
      track: { preview_url: 'http://x/y2.mp3', genre: 'pop' },
    })
    await flushPromises()

    expect(wrapper.find('.mystery-orb').exists()).toBe(true)
    expect(wrapper.find('img.reveal-cover').exists()).toBe(false)
    const input = wrapper.get('input.input-answer')
    expect((input.element as HTMLInputElement).disabled).toBe(false)
  })

  it('exposes cover, title and artist during playing_reveal phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing_reveal',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop', cover_url: 'http://c/o.jpg' },
      round_results: {
        correct_title: 'Thriller',
        correct_artist: 'Michael Jackson',
        cover_url: 'http://c/o.jpg',
      },
    })
    expect(wrapper.text()).toContain('Thriller')
    expect(wrapper.text()).toContain('Michael Jackson')
    const img = wrapper.find('img.reveal-cover')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('http://c/o.jpg')
  })

  it('disables AnswerInput during playing_reveal phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing_reveal',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop', cover_url: 'http://c/o.jpg' },
      round_results: {
        correct_title: 'Thriller',
        correct_artist: 'Michael Jackson',
        cover_url: 'http://c/o.jpg',
      },
    })
    const input = wrapper.get('input.input-answer')
    expect((input.element as HTMLInputElement).disabled).toBe(true)
  })

  it('keeps the audio element mounted across playing → playing_reveal transition', async () => {
    const { wrapper, game } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    await flushPromises()
    const audioBefore = wrapper.find('audio').element
    expect(audioBefore).toBeTruthy()

    game.setState({
      phase: 'playing_reveal',
      current_round: 0,
      total_rounds: 5,
      total_scores: { u1: 0, u2: 0 },
      track: { preview_url: 'http://x/y.mp3', genre: 'pop', cover_url: 'http://c/o.jpg' },
      round_results: {
        correct_title: 'Thriller',
        correct_artist: 'Michael Jackson',
        cover_url: 'http://c/o.jpg',
      },
    })
    await flushPromises()

    const audioAfter = wrapper.find('audio').element
    expect(audioAfter).toBe(audioBefore)
  })

  it('renders the pause stage during round_pause phase', async () => {
    const { wrapper } = await setup({ phase: 'round_pause' })
    expect(wrapper.find('.pause-stage').exists()).toBe(true)
    expect(wrapper.find('input.input-answer').exists()).toBe(false)
  })

  it('pauses the audio element when entering round_pause from playing_reveal', async () => {
    const pauseSpy = vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
    try {
      const { wrapper, game } = await setup({
        phase: 'playing_reveal',
        track: { preview_url: 'http://x/y.mp3', genre: 'pop', cover_url: 'http://c/o.jpg' },
        round_results: {
          correct_title: 'Thriller',
          correct_artist: 'Michael Jackson',
          cover_url: 'http://c/o.jpg',
        },
      })
      await flushPromises()
      expect(wrapper.find('audio').exists()).toBe(true)
      pauseSpy.mockClear()

      game.setState({
        phase: 'round_pause',
        current_round: 0,
        total_rounds: 5,
        total_scores: { u1: 0, u2: 0 },
      })
      await flushPromises()

      expect(pauseSpy).toHaveBeenCalled()
    } finally {
      pauseSpy.mockRestore()
    }
  })

  it('host sees back-to-lobby button in finished phase and it routes to /:code', async () => {
    const { wrapper, router } = await setup(
      {
        phase: 'finished',
      },
      { isHost: true },
    )
    const btn = wrapper.find('[data-test="back-lobby"]')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/FUNK4242')
  })

  it('does not show back-to-lobby button for non-host in finished phase', async () => {
    const { wrapper } = await setup({ phase: 'finished' }, { isHost: false })
    expect(wrapper.find('[data-test="back-lobby"]').exists()).toBe(false)
  })

  it('attaches the audio element to useVolume when entering playing phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    await flushPromises()
    expect(attachMusicMock).toHaveBeenCalled()
    const arg = attachMusicMock.mock.calls[0]?.[0]
    expect(arg).toBe(wrapper.find('audio').element)
  })

  it('detaches the music binding on unmount', async () => {
    const detach = vi.fn()
    attachMusicMock.mockImplementation(() => detach)
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    await flushPromises()
    wrapper.unmount()
    expect(detach).toHaveBeenCalled()
  })
})

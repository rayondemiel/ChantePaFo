import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import BlindtestRound from '../../src/components/BlindtestRound.vue'
import { useAuthStore } from '../../src/stores/auth'
import { useRoomStore } from '../../src/stores/room'
import { useGameStore } from '../../src/stores/game'
import type { GameState, FuzzyResult, MatchInfo } from '../../src/types'

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

const connectAmbianceAudioMock = vi.fn()
vi.mock('../../src/composables/useAmbiance', () => ({
  useAmbiance: () => ({
    start: vi.fn(),
    stop: vi.fn(),
    connectAudio: connectAmbianceAudioMock,
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
    connectAmbianceAudioMock.mockClear()
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

  it('declares crossorigin="anonymous" on the <audio> element so the FFT analyser is not CORS-tainted', async () => {
    // Without this attribute, MediaElementAudioSource zeroes the entire
    // graph (including destination) when the source is cross-origin —
    // muting playback. Deezer's CDN returns ACAO `*` so the combo works.
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const audio = wrapper.find('audio')
    expect(audio.exists()).toBe(true)
    expect(audio.attributes('crossorigin')).toBe('anonymous')
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

  it('renders score total in sidebar during playing phase on desktop', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
      total_scores: { u1: 5, u2: 3 },
    })
    const scoreboard = wrapper.findComponent({ name: 'ScoreBoard' })
    expect(scoreboard.exists()).toBe(true)
    const rows = wrapper.findAll('.score-row')
    expect(rows.length).toBe(2)
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
      payload: { text: string }
    }
    expect(payload.code).toBe('FUNK4242')
    expect(payload).not.toHaveProperty('player_id')
    expect(payload.payload.text).toBe('Thriller')
    // time_ms is no longer client-supplied — the server stamps it from its
    // monotonic clock to prevent the "send time_ms=0 every round" cheat.
    expect(payload.payload).not.toHaveProperty('time_ms')
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

  it('renders ScoreBoard during round_pause phase', async () => {
    const { wrapper } = await setup({
      phase: 'round_pause',
      total_scores: { u1: 10, u2: 7 },
    })
    const scoreboard = wrapper.findComponent({ name: 'ScoreBoard' })
    expect(scoreboard.exists()).toBe(true)
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

  it('host sees back-to-lobby and replay buttons in finished phase', async () => {
    const { wrapper } = await setup(
      {
        phase: 'finished',
      },
      { isHost: true },
    )
    const lobbyBtn = wrapper.find('[data-test="back-lobby"]')
    expect(lobbyBtn.exists()).toBe(true)
    const replayBtn = wrapper.find('[data-test="replay-game"]')
    expect(replayBtn.exists()).toBe(true)
  })

  it('return-to-lobby button emits return_to_lobby event', async () => {
    const { wrapper } = await setup({ phase: 'finished' }, { isHost: true })
    await wrapper.find('[data-test="back-lobby"]').trigger('click')
    await flushPromises()
    const call = socketMock.emit.mock.calls.find((c) => c[0] === 'return_to_lobby')
    expect(call).toBeDefined()
    expect(call![1]).toEqual({ code: 'FUNK4242' })
  })

  it('replay button emits replay_game event', async () => {
    const { wrapper } = await setup({ phase: 'finished' }, { isHost: true })
    await wrapper.find('[data-test="replay-game"]').trigger('click')
    await flushPromises()
    const call = socketMock.emit.mock.calls.find((c) => c[0] === 'replay_game')
    expect(call).toBeDefined()
    expect(call![1]).toEqual({ code: 'FUNK4242' })
  })

  it('finished phase shows waiting message for non-host', async () => {
    const { wrapper } = await setup({ phase: 'finished' }, { isHost: false })
    expect(wrapper.find('[data-test="back-lobby"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="replay-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="waiting-host"]').exists()).toBe(true)
    expect(wrapper.text()).toContain("En attente de l'hôte")
  })

  it('finished phase shows awards from game store', async () => {
    const { wrapper, game } = await setup({ phase: 'finished' }, { isHost: false })
    game.setFinalResults({
      awards: [
        {
          id: 'maestro',
          title: 'Le Maestro',
          emoji: '\uD83C\uDFC6',
          player_id: 'u1',
          player_name: 'Alice',
          detail: 'Alice avec 42 pts',
        },
      ],
      total_scores: { u1: 42, u2: 10 },
    })
    await flushPromises()
    expect(wrapper.find('.awards-ceremony').exists()).toBe(true)
    expect(wrapper.text()).toContain('Le Maestro')
    expect(wrapper.text()).toContain('Alice')
  })

  describe('setlist recap (finished ceremony)', () => {
    interface TracklistOverrides {
      round?: number
      title?: string
      artist?: string
      cover_url?: string
      first_title?: { player_id: string; name: string; time_ms: number } | null
      first_artist?: { player_id: string; name: string; time_ms: number } | null
      nobody_found?: boolean
    }
    function tlEntry(over: TracklistOverrides = {}) {
      return {
        round: 1,
        title: 'Thriller',
        artist: 'Michael Jackson',
        cover_url: 'https://cover/1',
        first_title: null,
        first_artist: null,
        nobody_found: false,
        ...over,
      }
    }

    async function finishedWith(tracklist: ReturnType<typeof tlEntry>[]) {
      const { wrapper, game } = await setup({ phase: 'finished' }, { isHost: false })
      game.setFinalResults({ awards: [], total_scores: {}, tracklist })
      await flushPromises()
      return wrapper
    }

    it('renders one setlist row per played track with title and artist', async () => {
      const wrapper = await finishedWith([
        tlEntry({ round: 1 }),
        tlEntry({ round: 2, title: 'Billie Jean', artist: 'MJ' }),
      ])
      expect(wrapper.text()).toContain('Setlist')
      const rows = wrapper.findAll('.setlist-row')
      expect(rows).toHaveLength(2)
      expect(rows[0].text()).toContain('Thriller')
      expect(rows[1].text()).toContain('Billie Jean')
    })

    it('split case: a title chip and an artist chip credit two different players', async () => {
      const wrapper = await finishedWith([
        tlEntry({
          first_title: { player_id: 'u1', name: 'Alice', time_ms: 2300 },
          first_artist: { player_id: 'u2', name: 'Bob', time_ms: 5000 },
        }),
      ])
      const row = wrapper.get('.setlist-row')
      const titleChip = row.get('.setlist-chip.chip-title')
      const artistChip = row.get('.setlist-chip.chip-artist')
      expect(titleChip.text()).toContain('Alice')
      expect(artistChip.text()).toContain('Bob')
      expect(row.classes()).toContain('setlist-row--split')
    })

    it('parfait case: one fused chip when the same player took both firsts', async () => {
      const wrapper = await finishedWith([
        tlEntry({
          first_title: { player_id: 'u1', name: 'Alice', time_ms: 2300 },
          first_artist: { player_id: 'u1', name: 'Alice', time_ms: 4100 },
        }),
      ])
      const row = wrapper.get('.setlist-row')
      expect(row.classes()).toContain('setlist-row--parfait')
      const chips = row.findAll('.setlist-chip')
      expect(chips).toHaveLength(1)
      expect(chips[0].classes()).toContain('chip-parfait')
      expect(chips[0].text()).toContain('★')
      expect(chips[0].text()).toContain('Alice')
    })

    it('title-only: a ghost chip marks the unfound artist', async () => {
      const wrapper = await finishedWith([
        tlEntry({ first_title: { player_id: 'u1', name: 'Alice', time_ms: 2300 } }),
      ])
      const row = wrapper.get('.setlist-row')
      expect(row.find('.setlist-chip.chip-title').exists()).toBe(true)
      const ghost = row.get('.setlist-chip.chip-ghost')
      expect(ghost.text().toLowerCase()).toContain('artiste')
    })

    it('nobody found: ghost row with the crickets beat', async () => {
      const wrapper = await finishedWith([tlEntry({ nobody_found: true })])
      const row = wrapper.get('.setlist-row')
      expect(row.classes()).toContain('setlist-row--nobody')
      expect(row.text()).toContain('Personne')
      expect(row.text()).toContain('🦗')
    })

    it('the fastest title snipe of the game gets the lightning accent', async () => {
      const wrapper = await finishedWith([
        tlEntry({ round: 1, first_title: { player_id: 'u1', name: 'Alice', time_ms: 5000 } }),
        tlEntry({ round: 2, first_title: { player_id: 'u2', name: 'Bob', time_ms: 1800 } }),
      ])
      const rows = wrapper.findAll('.setlist-row')
      expect(rows[0].text()).not.toContain('⚡')
      expect(rows[1].text()).toContain('⚡')
    })
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

  it('connects the audio element to the ambiance analyser when entering playing phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    await flushPromises()
    expect(connectAmbianceAudioMock).toHaveBeenCalled()
    expect(connectAmbianceAudioMock.mock.calls[0]?.[0]).toBe(wrapper.find('audio').element)
  })

  it('renders CircularCountdown during playing phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
      extract_duration: 30,
    })
    const cc = wrapper.findComponent({ name: 'CircularCountdown' })
    expect(cc.exists()).toBe(true)
    expect(cc.props('running')).toBe(true)
    expect(cc.props('duration')).toBe(25)
  })

  it('falls back to 25s when extract_duration is missing', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const cc = wrapper.findComponent({ name: 'CircularCountdown' })
    expect(cc.props('duration')).toBe(25)
  })

  it('keeps CircularCountdown running when locallyFound is true', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
      extract_duration: 30,
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
    const cc = wrapper.findComponent({ name: 'CircularCountdown' })
    expect(cc.exists()).toBe(true)
    expect(cc.props('running')).toBe(true)
  })

  it('does not render CircularCountdown during playing_reveal', async () => {
    const { wrapper } = await setup({
      phase: 'playing_reveal',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop', cover_url: 'http://c/o.jpg' },
      round_results: {
        correct_title: 'Thriller',
        correct_artist: 'Michael Jackson',
        cover_url: 'http://c/o.jpg',
      },
    })
    const cc = wrapper.findComponent({ name: 'CircularCountdown' })
    expect(cc.exists()).toBe(false)
  })

  it('renders RoundPodium with winners during playing_reveal phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing_reveal',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop', cover_url: 'http://c/o.jpg' },
      round_results: {
        correct_title: 'Thriller',
        correct_artist: 'Michael Jackson',
        cover_url: 'http://c/o.jpg',
        winners: [
          { player_id: 'u1', name: 'Alice', time_ms: 1500 },
          { player_id: 'u2', name: 'Bob', time_ms: 3200 },
        ],
      },
    })
    const podium = wrapper.findComponent({ name: 'RoundPodium' })
    expect(podium.exists()).toBe(true)
    expect(podium.props('winners')).toHaveLength(2)
    expect(wrapper.text()).toContain('Alice')
  })

  it('does not render RoundPodium during playing', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const podium = wrapper.findComponent({ name: 'RoundPodium' })
    expect(podium.exists()).toBe(false)
  })

  it('subscribes to player_match on mount and unsubscribes on unmount', async () => {
    const { wrapper } = await setup({ phase: 'playing' })
    const subscribed = socketMock.on.mock.calls.map((c) => c[0])
    expect(subscribed).toContain('player_match')
    wrapper.unmount()
    const unsubscribed = socketMock.off.mock.calls.map((c) => c[0])
    expect(unsubscribed).toContain('player_match')
  })

  it('shows match status in live ranking when player_match is received', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const call = socketMock.on.mock.calls.find((c) => c[0] === 'player_match')
    const handler = call![1] as (d: unknown) => void
    handler({ player_id: 'u2', time_ms: 3200, match_type: 'title' })
    await flushPromises()

    const ranking = wrapper.find('.live-ranking')
    expect(ranking.exists()).toBe(true)
    const rows = wrapper.findAll('.ranking-row')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Bob')
    expect(rows[0].classes()).toContain('ranking-partial')
  })

  it('upgrades match status in live ranking when player sends bonus', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const call = socketMock.on.mock.calls.find((c) => c[0] === 'player_match')
    const handler = call![1] as (d: unknown) => void
    handler({ player_id: 'u2', time_ms: 3200, match_type: 'title' })
    handler({ player_id: 'u2', time_ms: 4000, match_type: 'bonus' })
    await flushPromises()
    const bobRow = wrapper.findAll('.ranking-row').find((r) => r.text().includes('Bob'))
    expect(bobRow!.classes()).toContain('ranking-bonus')
  })

  it('resets live ranking match status when entering the next round', async () => {
    const { wrapper, game } = await setup({
      phase: 'playing',
      current_round: 0,
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
    })
    const call = socketMock.on.mock.calls.find((c) => c[0] === 'player_match')
    const handler = call![1] as (d: unknown) => void
    handler({ player_id: 'u2', time_ms: 3200, match_type: 'title' })
    await flushPromises()
    expect(wrapper.find('.ranking-partial').exists()).toBe(true)

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

    expect(wrapper.find('.ranking-partial').exists()).toBe(false)
    expect(wrapper.find('.ranking-bonus').exists()).toBe(false)
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

  it('renders TrackWaveform during playing phase', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
      extract_duration: 30,
    })
    const waveform = wrapper.findComponent({ name: 'TrackWaveform' })
    expect(waveform.exists()).toBe(true)
    expect(waveform.props('frozen')).toBe(false)
    expect(waveform.props('markers')).toEqual([])
  })

  it('passes frozen=true and markers to TrackWaveform during playing_reveal', async () => {
    const markers: MatchInfo[] = [
      { player_id: 'u1', name: 'Alice', time_ms: 3000, match_type: 'bonus' },
    ]
    const { wrapper } = await setup({
      phase: 'playing_reveal',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop', cover_url: 'http://c/o.jpg' },
      round_results: {
        correct_title: 'Thriller',
        correct_artist: 'Michael Jackson',
        cover_url: 'http://c/o.jpg',
        winners: [],
        all_matches: markers,
      },
    })
    const waveform = wrapper.findComponent({ name: 'TrackWaveform' })
    expect(waveform.exists()).toBe(true)
    expect(waveform.props('frozen')).toBe(true)
    expect(waveform.props('markers')).toEqual(markers)
  })

  it('does not apply stress-pulse class when timeRemaining > 10', async () => {
    const { wrapper } = await setup({
      phase: 'playing',
      track: { preview_url: 'http://x/y.mp3', genre: 'pop' },
      extract_duration: 30,
    })
    expect(wrapper.find('.stress-pulse').exists()).toBe(false)
  })
})

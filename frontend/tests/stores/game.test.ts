import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGameStore } from '../../src/stores/game'

describe('game store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('starts with null state', () => {
    const store = useGameStore()
    expect(store.state).toBeNull()
    expect(store.awards).toEqual([])
  })

  it('setState sets the game state', () => {
    const store = useGameStore()
    store.setState({ phase: 'playing', current_round: 0, total_rounds: 5, total_scores: {} })
    expect(store.state?.phase).toBe('playing')
  })

  it('setFinalResults stores awards and scores', () => {
    const store = useGameStore()
    store.setFinalResults({
      awards: [
        {
          id: 'maestro',
          title: 'Le Maestro',
          emoji: '🏆',
          player_id: 'u1',
          player_name: 'Alice',
          detail: '2000 pts',
        },
      ],
      total_scores: { u1: 2000 },
    })
    expect(store.awards).toHaveLength(1)
    expect(store.finalScores['u1']).toBe(2000)
  })

  it('setFinalResults keeps the played tracklist for the ceremony', () => {
    const store = useGameStore()
    store.setFinalResults({
      awards: [],
      total_scores: {},
      tracklist: [
        {
          round: 1,
          title: 'Thriller',
          artist: 'Michael Jackson',
          cover_url: '',
          first_title: { player_id: 'u1', name: 'Alice', time_ms: 2300 },
          first_artist: null,
          nobody_found: false,
        },
      ],
    })
    expect(store.tracklist).toHaveLength(1)
    expect(store.tracklist[0].title).toBe('Thriller')
    expect(store.tracklist[0].first_title?.name).toBe('Alice')
  })

  it('reset clears everything', () => {
    const store = useGameStore()
    store.setState({ phase: 'playing', current_round: 0, total_rounds: 5, total_scores: {} })
    store.setFinalResults({
      awards: [],
      total_scores: {},
      tracklist: [
        {
          round: 1,
          title: 'T',
          artist: 'A',
          cover_url: '',
          first_title: null,
          first_artist: null,
          nobody_found: true,
        },
      ],
    })
    store.reset()
    expect(store.state).toBeNull()
    expect(store.awards).toEqual([])
    expect(store.tracklist).toEqual([])
  })
})

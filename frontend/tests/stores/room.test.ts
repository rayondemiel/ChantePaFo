import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useRoomStore } from '../../src/stores/room'
import { useAuthStore } from '../../src/stores/auth'

describe('room store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('starts with null room', () => {
    const store = useRoomStore()
    expect(store.room).toBeNull()
    expect(store.isHost).toBe(false)
  })

  it('setRoom stores the room', () => {
    const store = useRoomStore()
    store.setRoom({
      code: 'FUNK1234',
      players: [{ id: 'u1', name: 'Alice', is_host: true }],
      settings: {
        game_mode: 'blindtest',
        genres: { all: 2 },
        num_rounds: 10,
        extract_duration: 20,
        karaoke_variant: 'classic',
      },
      status: 'lobby',
    })
    expect(store.room?.code).toBe('FUNK1234')
  })

  it('isHost returns true when current user is host', () => {
    const auth = useAuthStore()
    auth.setAuth({ token: 'x', username: 'alice', user_id: 'u1' })
    const store = useRoomStore()
    store.setRoom({
      code: 'FUNK1234',
      players: [{ id: 'u1', name: 'Alice', is_host: true }],
      settings: {
        game_mode: 'blindtest',
        genres: { all: 2 },
        num_rounds: 10,
        extract_duration: 20,
        karaoke_variant: 'classic',
      },
      status: 'lobby',
    })
    expect(store.isHost).toBe(true)
  })

  it('isHost returns false for non-host', () => {
    const auth = useAuthStore()
    auth.setAuth({ token: 'x', username: 'bob', user_id: 'u2' })
    const store = useRoomStore()
    store.setRoom({
      code: 'FUNK1234',
      players: [
        { id: 'u1', name: 'Alice', is_host: true },
        { id: 'u2', name: 'Bob', is_host: false },
      ],
      settings: {
        game_mode: 'blindtest',
        genres: { all: 2 },
        num_rounds: 10,
        extract_duration: 20,
        karaoke_variant: 'classic',
      },
      status: 'lobby',
    })
    expect(store.isHost).toBe(false)
  })

  it('clearRoom resets to null', () => {
    const store = useRoomStore()
    store.setRoom({
      code: 'FUNK1234',
      players: [],
      settings: {
        game_mode: 'blindtest',
        genres: { all: 2 },
        num_rounds: 10,
        extract_duration: 20,
        karaoke_variant: 'classic',
      },
      status: 'lobby',
    })
    store.clearRoom()
    expect(store.room).toBeNull()
  })
})

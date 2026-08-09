import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { useAmbianceStore } from '../../src/stores/ambiance'

describe('ambiance store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  afterEach(() => {
    document.documentElement.style.removeProperty('--ambiance-color-1')
    document.documentElement.style.removeProperty('--ambiance-color-2')
    document.documentElement.style.removeProperty('--ambiance-intensity')
    document.documentElement.style.removeProperty('--ambiance-pulse-speed')
  })

  it('starts with lobby defaults', () => {
    const store = useAmbianceStore()
    expect(store.config.vibe).toBe('lobby')
    expect(store.config.intensity).toBe(0.2)
  })

  it('setAmbiance updates config', () => {
    const store = useAmbianceStore()
    store.setAmbiance({
      palette: ['#FF0000', '#00FF00'],
      behavior: 'pulse_fast',
      intensity: 0.9,
      vibe: 'disco',
    })
    expect(store.config.vibe).toBe('disco')
    expect(store.config.palette[0]).toBe('#FF0000')
  })

  it('syncs --ambiance-pulse-speed from the config bpm (one beat period)', async () => {
    const store = useAmbianceStore()
    store.setAmbiance({
      palette: ['#FF0000', '#00FF00'],
      behavior: 'pulse_fast',
      intensity: 0.9,
      vibe: 'disco',
      bpm: 120,
    })
    await nextTick()
    expect(document.documentElement.style.getPropertyValue('--ambiance-pulse-speed')).toBe('0.500s')
  })

  it('clamps --ambiance-pulse-speed for out-of-range bpm values', async () => {
    const store = useAmbianceStore()
    store.setAmbiance({
      palette: ['#FF0000', '#00FF00'],
      behavior: 'breathe_slow',
      intensity: 0.3,
      vibe: 'ambient',
      bpm: 20,
    })
    await nextTick()
    expect(document.documentElement.style.getPropertyValue('--ambiance-pulse-speed')).toBe('1.500s')
  })

  it('leaves --ambiance-pulse-speed untouched when bpm is absent', async () => {
    const store = useAmbianceStore()
    store.setAmbiance({
      palette: ['#FF0000', '#00FF00'],
      behavior: 'wave_smooth',
      intensity: 0.5,
      vibe: 'pop',
    })
    await nextTick()
    expect(document.documentElement.style.getPropertyValue('--ambiance-pulse-speed')).toBe('')
  })

  it('syncs CSS variables on update', async () => {
    const store = useAmbianceStore()
    store.setAmbiance({
      palette: ['#FF2D95', '#00F0FF'],
      behavior: 'wave',
      intensity: 0.7,
      vibe: 'pop',
    })
    await nextTick()
    expect(document.documentElement.style.getPropertyValue('--ambiance-color-1')).toBe('#FF2D95')
    expect(document.documentElement.style.getPropertyValue('--ambiance-intensity')).toBe('0.7')
  })
})

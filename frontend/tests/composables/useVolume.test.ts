import { describe, it, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'

async function freshUseVolume() {
  vi.resetModules()
  const mod = await import('../../src/composables/useVolume')
  return mod.useVolume()
}

function fakeAudio(): HTMLAudioElement {
  return { volume: 1 } as unknown as HTMLAudioElement
}

describe('useVolume', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('defaults to 0.8 unmuted when no localStorage values exist', async () => {
    const v = await freshUseVolume()
    expect(v.music.value).toBe(0.8)
    expect(v.musicMuted.value).toBe(false)
  })

  it('restores values from localStorage on first import', async () => {
    localStorage.setItem('chantepafo_volume_music', '0.42')
    localStorage.setItem('chantepafo_volume_music_muted', '1')
    const v = await freshUseVolume()
    expect(v.music.value).toBeCloseTo(0.42)
    expect(v.musicMuted.value).toBe(true)
  })

  it('falls back to defaults when localStorage holds garbage', async () => {
    localStorage.setItem('chantepafo_volume_music', 'not-a-number')
    localStorage.setItem('chantepafo_volume_music_muted', 'maybe')
    const v = await freshUseVolume()
    expect(v.music.value).toBe(0.8)
    expect(v.musicMuted.value).toBe(false)
  })

  it('setMusic(0.5) updates the ref and persists to localStorage', async () => {
    const v = await freshUseVolume()
    v.setMusic(0.5)
    expect(v.music.value).toBe(0.5)
    expect(localStorage.getItem('chantepafo_volume_music')).toBe('0.5')
  })

  it('setMusic(-1) clamps to 0', async () => {
    const v = await freshUseVolume()
    v.setMusic(-1)
    expect(v.music.value).toBe(0)
  })

  it('setMusic(2) clamps to 1', async () => {
    const v = await freshUseVolume()
    v.setMusic(2)
    expect(v.music.value).toBe(1)
  })

  it('toggleMusicMute inverts the muted state and persists it', async () => {
    const v = await freshUseVolume()
    expect(v.musicMuted.value).toBe(false)
    v.toggleMusicMute()
    expect(v.musicMuted.value).toBe(true)
    expect(localStorage.getItem('chantepafo_volume_music_muted')).toBe('1')
    v.toggleMusicMute()
    expect(v.musicMuted.value).toBe(false)
    expect(localStorage.getItem('chantepafo_volume_music_muted')).toBe('0')
  })

  it('attachMusic sets el.volume immediately to the current effective value', async () => {
    const v = await freshUseVolume()
    v.setMusic(0.6)
    const el = fakeAudio()
    v.attachMusic(el)
    expect(el.volume).toBeCloseTo(0.6)
  })

  it('propagates setMusic changes to attached elements via watcher', async () => {
    const v = await freshUseVolume()
    const el = fakeAudio()
    v.attachMusic(el)
    v.setMusic(0.3)
    await nextTick()
    expect(el.volume).toBeCloseTo(0.3)
  })

  it('forces el.volume to 0 while muted and restores on unmute', async () => {
    const v = await freshUseVolume()
    v.setMusic(0.7)
    const el = fakeAudio()
    v.attachMusic(el)
    expect(el.volume).toBeCloseTo(0.7)
    v.toggleMusicMute()
    await nextTick()
    expect(el.volume).toBe(0)
    v.toggleMusicMute()
    await nextTick()
    expect(el.volume).toBeCloseTo(0.7)
  })

  it('detach() stops further volume propagation to that element', async () => {
    const v = await freshUseVolume()
    const el = fakeAudio()
    const detach = v.attachMusic(el)
    v.setMusic(0.4)
    await nextTick()
    expect(el.volume).toBeCloseTo(0.4)
    detach()
    v.setMusic(0.9)
    await nextTick()
    expect(el.volume).toBeCloseTo(0.4)
  })

  it('does not crash and keeps defaults when localStorage.setItem throws', async () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota')
    })
    const v = await freshUseVolume()
    expect(() => v.setMusic(0.25)).not.toThrow()
    expect(v.music.value).toBe(0.25)
    expect(() => v.toggleMusicMute()).not.toThrow()
    expect(v.musicMuted.value).toBe(true)
    setItem.mockRestore()
  })

  it('does not crash when localStorage.getItem throws on init', async () => {
    const getItem = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const v = await freshUseVolume()
    expect(v.music.value).toBe(0.8)
    expect(v.musicMuted.value).toBe(false)
    getItem.mockRestore()
  })

  it('shares state across calls within the same module instance', async () => {
    vi.resetModules()
    const mod = await import('../../src/composables/useVolume')
    const a = mod.useVolume()
    const b = mod.useVolume()
    a.setMusic(0.33)
    expect(b.music.value).toBeCloseTo(0.33)
  })
})

import { ref, readonly, watch, type Ref } from 'vue'

const STORAGE_KEY_MUSIC = 'chantepafo_volume_music'
const STORAGE_KEY_MUSIC_MUTED = 'chantepafo_volume_music_muted'
const DEFAULT_MUSIC = 0.8

function clamp01(value: number): number {
  if (value < 0) return 0
  if (value > 1) return 1
  return value
}

function safeRead(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeWrite(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // private mode / quota — fall back to in-memory only
  }
}

function loadInitialMusic(): number {
  const raw = safeRead(STORAGE_KEY_MUSIC)
  if (raw === null) return DEFAULT_MUSIC
  const parsed = Number.parseFloat(raw)
  if (!Number.isFinite(parsed)) return DEFAULT_MUSIC
  return clamp01(parsed)
}

function loadInitialMuted(): boolean {
  const raw = safeRead(STORAGE_KEY_MUSIC_MUTED)
  if (raw === '1') return true
  if (raw === '0') return false
  return false
}

const music: Ref<number> = ref(loadInitialMusic())
const musicMuted: Ref<boolean> = ref(loadInitialMuted())
const attached = new Set<HTMLAudioElement>()

function effectiveMusic(): number {
  return musicMuted.value ? 0 : music.value
}

function propagate(): void {
  const v = effectiveMusic()
  for (const el of attached) {
    el.volume = v
  }
}

watch([music, musicMuted], propagate)

function setMusic(value: number): void {
  const next = clamp01(value)
  music.value = next
  safeWrite(STORAGE_KEY_MUSIC, String(next))
}

function toggleMusicMute(): void {
  musicMuted.value = !musicMuted.value
  safeWrite(STORAGE_KEY_MUSIC_MUTED, musicMuted.value ? '1' : '0')
}

function attachMusic(el: HTMLAudioElement): () => void {
  el.volume = effectiveMusic()
  attached.add(el)
  return () => {
    attached.delete(el)
  }
}

export function useVolume() {
  return {
    music: readonly(music),
    musicMuted: readonly(musicMuted),
    setMusic,
    toggleMusicMute,
    attachMusic,
  }
}

import { onUnmounted } from 'vue'
import { useAmbianceStore } from '../stores/ambiance'
import { useAudio } from './useAudio'

// The store already syncs palette + base intensity into CSS variables
// (--ambiance-color-1/2, --ambiance-intensity) whenever its config changes.
// This composable adds beat-reactive modulation on top, writing two vars
// each frame while audio plays:
//   --ambiance-intensity: base + (1 - base) * pulse — the pulse fills the
//     HEADROOM above the static base, so it stays visible even for genres
//     whose base intensity is already 0.9+ (a multiplicative formula clips
//     those at 1 and the beat disappears).
//   --ambiance-pulse: the smoothed bass envelope [0..1], for CSS effects
//     that want the raw beat (stripe scaleY, etc.).
// When the analyser sees silence (or isn't connected), both settle back to
// the static base / 0 — never below.
const PULSE_GAIN = 1.0
// Envelope follower: a bass hit lights up in ~2 frames, then glows out over
// ~15 — punchy but musical, instead of per-frame flicker.
const ATTACK = 0.5
const RELEASE = 0.12

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

export function useAmbiance() {
  const store = useAmbianceStore()
  const audio = useAudio()
  let animFrame = 0
  let running = false
  let smoothed = 0

  function renderFrame(): void {
    if (!running) return
    const root = document.documentElement
    const bass = audio.getBassLevel()
    smoothed += (bass - smoothed) * (bass > smoothed ? ATTACK : RELEASE)
    const pulse = Math.min(1, smoothed * PULSE_GAIN)
    const base = store.config.intensity
    const dynamic = Math.min(1, base + (1 - base) * pulse)
    root.style.setProperty('--ambiance-intensity', String(dynamic))
    root.style.setProperty('--ambiance-pulse', pulse.toFixed(3))
    animFrame = requestAnimationFrame(renderFrame)
  }

  function start(): void {
    if (running) return
    // Beat-synced opacity pulsing is exactly what photosensitive users opt
    // out of — leave the static ambiance in place for them.
    if (prefersReducedMotion()) return
    running = true
    renderFrame()
  }

  function stop(): void {
    running = false
    if (animFrame) cancelAnimationFrame(animFrame)
    animFrame = 0
    smoothed = 0
    // Restore the store's static base so the next start() doesn't inherit
    // a stale pulse value. The store's own watch will also overwrite this
    // on the next ambiance_update event.
    document.documentElement.style.setProperty(
      '--ambiance-intensity',
      String(store.config.intensity),
    )
    document.documentElement.style.setProperty('--ambiance-pulse', '0')
  }

  function connectAudio(el: HTMLAudioElement): void {
    // CALLER BEWARE: cross-origin <audio> elements must declare
    // crossorigin="anonymous" AND the server must return ACAO, otherwise
    // the browser zeroes the whole graph (silencing playback). Same-origin
    // sources (e.g. /uploads/*) work without the attribute. Deezer's
    // preview CDN returns ACAO `*` so blindtest <audio> works as long as
    // crossorigin="anonymous" is set.
    audio.connectAnalyser(el)
  }

  onUnmounted(stop)

  return { start, stop, connectAudio }
}

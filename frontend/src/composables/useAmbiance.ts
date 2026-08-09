import { onUnmounted } from 'vue'
import { useAmbianceStore } from '../stores/ambiance'
import { useAudio } from './useAudio'

// The store already syncs palette + base intensity into CSS variables
// (--ambiance-color-1/2, --ambiance-intensity) whenever its config changes.
// This composable adds beat-reactive intensity modulation on top: when audio
// plays, --ambiance-intensity pulses ABOVE the static base with the bass
// level. When the analyser sees silence (or isn't connected), it falls back
// to the store's base value — never goes below it.

// At bass=0 the multiplier is 1 (pulse is invisible → matches static base).
// At bass=1 the multiplier is 1+PULSE_GAIN. Tune PULSE_GAIN to taste.
const PULSE_GAIN = 1.0

export function useAmbiance() {
  const store = useAmbianceStore()
  const audio = useAudio()
  let animFrame = 0
  let running = false

  function renderFrame(): void {
    if (!running) return
    const root = document.documentElement
    const bass = audio.getBassLevel()
    const base = store.config.intensity
    const dynamic = base * (1 + bass * PULSE_GAIN)
    root.style.setProperty('--ambiance-intensity', String(Math.min(dynamic, 1)))
    animFrame = requestAnimationFrame(renderFrame)
  }

  function start(): void {
    if (running) return
    running = true
    renderFrame()
  }

  function stop(): void {
    running = false
    if (animFrame) cancelAnimationFrame(animFrame)
    animFrame = 0
    // Restore the store's static base so the next start() doesn't inherit
    // a stale pulse value. The store's own watch will also overwrite this
    // on the next ambiance_update event.
    document.documentElement.style.setProperty(
      '--ambiance-intensity',
      String(store.config.intensity),
    )
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

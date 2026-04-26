import { onUnmounted } from 'vue'
import { useAmbianceStore } from '../stores/ambiance'
import { useAudio } from './useAudio'

// The store already syncs palette + base intensity into CSS variables
// (--ambiance-color-1/2, --ambiance-intensity) whenever its config changes.
// This composable only adds beat-reactive intensity modulation: when audio
// is playing, --ambiance-intensity pulses with the bass level. When no
// analyser is connected, it leaves the static intensity untouched.

const PULSE_FLOOR = 0.6
const PULSE_RANGE = 0.8

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
    // No analyser yet → bass is 0; keep the static base so the visual stays
    // calm during countdown / lobby.
    if (bass > 0) {
      const dynamic = base * (PULSE_FLOOR + bass * PULSE_RANGE)
      root.style.setProperty('--ambiance-intensity', String(Math.min(dynamic, 1)))
    }
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
    // Reset to the store's static base so the next start() doesn't inherit
    // a stale pulse value if the audio was paused mid-beat.
    document.documentElement.style.setProperty(
      '--ambiance-intensity',
      String(store.config.intensity),
    )
  }

  function connectAudio(el: HTMLAudioElement): void {
    audio.connectAnalyser(el)
  }

  onUnmounted(stop)

  return { start, stop, connectAudio }
}

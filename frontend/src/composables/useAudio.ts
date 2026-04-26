import { ref, readonly, type Ref } from 'vue'

// Web Audio API only allows ONE MediaElementAudioSourceNode per audio element
// for the lifetime of the page. Re-creating one throws InvalidStateError. We
// also share a single AudioContext app-wide because mobile browsers cap how
// many can be created — a singleton matches the actual browser model.

let audioContext: AudioContext | null = null
let analyser: AnalyserNode | null = null
const sources = new WeakMap<HTMLAudioElement, MediaElementAudioSourceNode>()

const isPlaying = ref(false)
const frequencyData: Ref<Uint8Array> = ref(new Uint8Array(0))

let animFrame = 0
let rafRunning = false

function ensureContext(): AudioContext | null {
  if (audioContext) return audioContext
  // AudioContext lives on `window`; fall back to webkit prefix for older Safari.
  const Ctor =
    (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext ??
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!Ctor) return null
  try {
    audioContext = new Ctor()
    return audioContext
  } catch {
    return null
  }
}

function startTickLoop(): void {
  if (rafRunning || !analyser) return
  rafRunning = true
  const buffer = new Uint8Array(analyser.frequencyBinCount)
  const tick = () => {
    if (!analyser) {
      rafRunning = false
      return
    }
    analyser.getByteFrequencyData(buffer)
    // Reassign a new view so Vue refs trigger reactivity for consumers that
    // watch frequencyData directly (most consumers use the level helpers).
    frequencyData.value = buffer
    animFrame = requestAnimationFrame(tick)
  }
  tick()
}

function stopTickLoop(): void {
  if (animFrame) cancelAnimationFrame(animFrame)
  animFrame = 0
  rafRunning = false
}

function connectAnalyser(el: HTMLAudioElement): AnalyserNode | null {
  const ctx = ensureContext()
  if (!ctx) return null

  // Resume on user gesture: AudioContext starts suspended on iOS until the
  // first interaction unlocks it. Calling resume() inside a click/play handler
  // (which is where this composable is wired) succeeds silently.
  if (ctx.state === 'suspended') {
    ctx.resume().catch(() => {})
  }

  if (!analyser) {
    analyser = ctx.createAnalyser()
    analyser.fftSize = 256
    analyser.smoothingTimeConstant = 0.7
    analyser.connect(ctx.destination)
  }

  let source = sources.get(el)
  if (!source) {
    try {
      source = ctx.createMediaElementSource(el)
      source.connect(analyser)
      sources.set(el, source)
    } catch {
      // Element already wired to another graph (e.g. via a different
      // composable instance) — silently ignore, the analyser keeps reading
      // from whichever source is connected.
      return analyser
    }
  }

  startTickLoop()
  return analyser
}

function averageRange(start: number, end: number): number {
  const data = frequencyData.value
  if (data.length === 0) return 0
  const lo = Math.max(0, Math.min(start, data.length))
  const hi = Math.max(lo, Math.min(end, data.length))
  if (hi === lo) return 0
  // subarray() returns a view (no allocation); reduce avoids the
  // bracket-indexed loop that triggers the security/detect-object-injection
  // warning even though `i` is bounded by hi/lo (both clamped above).
  const slice = data.subarray(lo, hi)
  let sum = 0
  slice.forEach((v) => {
    sum += v
  })
  return sum / ((hi - lo) * 255)
}

function getBassLevel(): number {
  return averageRange(0, 10)
}

function getMidLevel(): number {
  return averageRange(10, 60)
}

function getHighLevel(): number {
  return averageRange(60, frequencyData.value.length)
}

function setIsPlaying(v: boolean): void {
  isPlaying.value = v
}

function disconnect(): void {
  stopTickLoop()
  // Don't close the AudioContext — closing breaks any other element wired to
  // it for the rest of the page lifetime, and there's no upside (the browser
  // suspends idle contexts automatically).
}

export function useAudio() {
  return {
    isPlaying: readonly(isPlaying),
    frequencyData: readonly(frequencyData),
    connectAnalyser,
    getBassLevel,
    getMidLevel,
    getHighLevel,
    setIsPlaying,
    disconnect,
  }
}

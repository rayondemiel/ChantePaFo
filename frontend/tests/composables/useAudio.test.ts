import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// jsdom doesn't ship Web Audio. We install a controllable fake on `window`
// before importing the composable so its module-level state picks it up.

interface FakeAnalyser {
  fftSize: number
  smoothingTimeConstant: number
  frequencyBinCount: number
  connect: ReturnType<typeof vi.fn>
  getByteFrequencyData: (out: Uint8Array) => void
}

interface FakeContext {
  state: 'suspended' | 'running' | 'closed'
  destination: object
  resume: ReturnType<typeof vi.fn>
  createAnalyser: ReturnType<typeof vi.fn>
  createMediaElementSource: ReturnType<typeof vi.fn>
}

interface ContextHandle {
  ctx: FakeContext | null
  analyser: FakeAnalyser | null
  // Lets each test feed the analyser fresh frequency bytes.
  freqBytes: Uint8Array
  createSourceCalls: HTMLAudioElement[]
  createSourceShouldThrow: boolean
}

function makeAnalyser(handle: ContextHandle): FakeAnalyser {
  return {
    fftSize: 256,
    smoothingTimeConstant: 0.7,
    frequencyBinCount: 128,
    connect: vi.fn(),
    getByteFrequencyData(out: Uint8Array) {
      // Copy whatever the test placed in handle.freqBytes into the buffer
      // owned by the composable. The composable created the buffer with
      // length = frequencyBinCount (128).
      const n = Math.min(out.length, handle.freqBytes.length)
      for (let i = 0; i < n; i++) {
        // safe: i bounded by Math.min(out.length, freqBytes.length)
        // eslint-disable-next-line security/detect-object-injection
        out[i] = handle.freqBytes[i]
      }
    },
  }
}

function installFakeAudioContext(): ContextHandle {
  const handle: ContextHandle = {
    ctx: null,
    analyser: null,
    freqBytes: new Uint8Array(128),
    createSourceCalls: [],
    createSourceShouldThrow: false,
  }
  class FakeAudioContext {
    state: 'suspended' | 'running' | 'closed' = 'suspended'
    destination = {}
    resume = vi.fn().mockImplementation(() => {
      this.state = 'running'
      return Promise.resolve()
    })
    createAnalyser = vi.fn().mockImplementation(() => {
      handle.analyser = makeAnalyser(handle)
      return handle.analyser
    })
    createMediaElementSource = vi.fn().mockImplementation((el: HTMLAudioElement) => {
      handle.createSourceCalls.push(el)
      if (handle.createSourceShouldThrow) {
        throw new Error('InvalidStateError')
      }
      return { connect: vi.fn() }
    })
    constructor() {
      handle.ctx = this as unknown as FakeContext
    }
  }
  ;(window as unknown as { AudioContext: typeof AudioContext }).AudioContext =
    FakeAudioContext as unknown as typeof AudioContext
  return handle
}

function uninstallAudioContext(): void {
  // Defining AudioContext as undefined matches "not present" in the Ctor
  // lookup the composable does (it ?? webkit fallback ?? null).
  ;(window as unknown as { AudioContext: undefined }).AudioContext = undefined
  ;(window as unknown as { webkitAudioContext: undefined }).webkitAudioContext = undefined
}

function installRAF(): { tick: () => void } {
  // Manual RAF: we control when the tick loop reads the analyser, so tests
  // are deterministic and don't depend on real timers.
  const callbacks: Array<FrameRequestCallback> = []
  let id = 0
  ;(
    globalThis as unknown as { requestAnimationFrame: typeof requestAnimationFrame }
  ).requestAnimationFrame = (cb: FrameRequestCallback) => {
    callbacks.push(cb)
    return ++id
  }
  ;(
    globalThis as unknown as { cancelAnimationFrame: typeof cancelAnimationFrame }
  ).cancelAnimationFrame = () => {
    callbacks.length = 0
  }
  return {
    tick() {
      const pending = callbacks.splice(0)
      for (const cb of pending) cb(performance.now())
    },
  }
}

async function freshUseAudio() {
  vi.resetModules()
  const mod = await import('../../src/composables/useAudio')
  return mod.useAudio()
}

function fakeAudioEl(): HTMLAudioElement {
  return {} as unknown as HTMLAudioElement
}

describe('useAudio', () => {
  let ctxHandle: ContextHandle
  let raf: { tick: () => void }

  beforeEach(() => {
    ctxHandle = installFakeAudioContext()
    raf = installRAF()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns 0 for all level getters before any analyser is connected', async () => {
    const a = await freshUseAudio()
    expect(a.getBassLevel()).toBe(0)
    expect(a.getMidLevel()).toBe(0)
    expect(a.getHighLevel()).toBe(0)
  })

  it('connectAnalyser creates an AudioContext + analyser on first call', async () => {
    const a = await freshUseAudio()
    const result = a.connectAnalyser(fakeAudioEl())
    expect(result).not.toBeNull()
    expect(ctxHandle.ctx).not.toBeNull()
    expect(ctxHandle.analyser).not.toBeNull()
    expect(ctxHandle.ctx?.createAnalyser).toHaveBeenCalledOnce()
  })

  it('connectAnalyser returns null when no AudioContext constructor is available', async () => {
    uninstallAudioContext()
    const a = await freshUseAudio()
    const result = a.connectAnalyser(fakeAudioEl())
    expect(result).toBeNull()
    expect(a.getBassLevel()).toBe(0)
  })

  it('resumes a suspended AudioContext on connect', async () => {
    const a = await freshUseAudio()
    a.connectAnalyser(fakeAudioEl())
    expect(ctxHandle.ctx?.resume).toHaveBeenCalled()
    expect(ctxHandle.ctx?.state).toBe('running')
  })

  it('connectAnalyser is idempotent for the same audio element', async () => {
    const a = await freshUseAudio()
    const el = fakeAudioEl()
    a.connectAnalyser(el)
    a.connectAnalyser(el)
    a.connectAnalyser(el)
    // createMediaElementSource may legally only be called once per element.
    expect(ctxHandle.createSourceCalls.length).toBe(1)
    // The analyser is also a singleton — never recreated.
    expect(ctxHandle.ctx?.createAnalyser).toHaveBeenCalledOnce()
  })

  it('reuses the same analyser across distinct elements (different sources)', async () => {
    const a = await freshUseAudio()
    a.connectAnalyser(fakeAudioEl())
    a.connectAnalyser(fakeAudioEl())
    expect(ctxHandle.createSourceCalls.length).toBe(2)
    expect(ctxHandle.ctx?.createAnalyser).toHaveBeenCalledOnce()
  })

  it('swallows InvalidStateError from createMediaElementSource and still returns the analyser', async () => {
    ctxHandle.createSourceShouldThrow = true
    const a = await freshUseAudio()
    const result = a.connectAnalyser(fakeAudioEl())
    expect(result).not.toBeNull()
  })

  it('getBassLevel averages bins 0..10 from the analyser data after a tick', async () => {
    const a = await freshUseAudio()
    a.connectAnalyser(fakeAudioEl())
    // Bins 0..9 = 255 (max), the rest = 0 → bass should be 1.0, others 0.
    const bytes = new Uint8Array(128)
    bytes.fill(255, 0, 10)
    ctxHandle.freqBytes = bytes
    raf.tick()
    expect(a.getBassLevel()).toBeCloseTo(1, 5)
    expect(a.getMidLevel()).toBe(0)
    expect(a.getHighLevel()).toBe(0)
  })

  it('getMidLevel averages bins 10..60 only', async () => {
    const a = await freshUseAudio()
    a.connectAnalyser(fakeAudioEl())
    const bytes = new Uint8Array(128)
    bytes.fill(128, 10, 60)
    ctxHandle.freqBytes = bytes
    raf.tick()
    expect(a.getBassLevel()).toBe(0)
    expect(a.getMidLevel()).toBeCloseTo(128 / 255, 3)
    expect(a.getHighLevel()).toBe(0)
  })

  it('getHighLevel averages bins 60..end only', async () => {
    const a = await freshUseAudio()
    a.connectAnalyser(fakeAudioEl())
    const bytes = new Uint8Array(128)
    bytes.fill(64, 60, 128)
    ctxHandle.freqBytes = bytes
    raf.tick()
    expect(a.getHighLevel()).toBeCloseTo(64 / 255, 3)
    expect(a.getBassLevel()).toBe(0)
    expect(a.getMidLevel()).toBe(0)
  })

  it('setIsPlaying toggles the reactive ref', async () => {
    const a = await freshUseAudio()
    expect(a.isPlaying.value).toBe(false)
    a.setIsPlaying(true)
    expect(a.isPlaying.value).toBe(true)
    a.setIsPlaying(false)
    expect(a.isPlaying.value).toBe(false)
  })

  it('disconnect stops the RAF tick loop (subsequent ticks become no-ops)', async () => {
    const a = await freshUseAudio()
    a.connectAnalyser(fakeAudioEl())
    const bytes = new Uint8Array(128)
    bytes.fill(255, 0, 10)
    ctxHandle.freqBytes = bytes
    raf.tick()
    expect(a.getBassLevel()).toBeCloseTo(1, 5)

    a.disconnect()
    // After disconnect, zero out and tick — getBassLevel must read the
    // stale buffer (or empty) but the RAF callback chain has been cancelled
    // so no new analyser reads happen. We assert no further reads by
    // changing freqBytes and ticking — the level should stay where it was.
    ctxHandle.freqBytes = new Uint8Array(128) // all zeros now
    raf.tick()
    expect(a.getBassLevel()).toBeCloseTo(1, 5)
  })

  it('shares state across calls within the same module instance', async () => {
    vi.resetModules()
    const mod = await import('../../src/composables/useAudio')
    const a = mod.useAudio()
    const b = mod.useAudio()
    a.setIsPlaying(true)
    expect(b.isPlaying.value).toBe(true)
  })
})

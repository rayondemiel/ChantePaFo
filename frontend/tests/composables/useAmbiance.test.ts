import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, type ComponentPublicInstance } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { useAmbianceStore } from '../../src/stores/ambiance'
import { useAmbiance } from '../../src/composables/useAmbiance'

// The beat loop reads useAudio().getBassLevel() each frame. Mock the module
// with a controllable level; the extra __setBass export is test-only.
vi.mock('../../src/composables/useAudio', () => {
  const state = { bass: 0 }
  return {
    useAudio: () => ({
      getBassLevel: () => state.bass,
      connectAnalyser: vi.fn(),
    }),
    __setBass: (v: number) => {
      state.bass = v
    },
  }
})

type AudioMockModule = typeof import('../../src/composables/useAudio') & {
  __setBass: (v: number) => void
}
const audioMock = (await import('../../src/composables/useAudio')) as AudioMockModule

// Manual RAF so each frame of the pulse loop runs exactly when the test says.
function installRAF(): { tick: (n?: number) => void } {
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
    tick(n = 1) {
      for (let i = 0; i < n; i++) {
        const pending = callbacks.splice(0)
        for (const cb of pending) cb(performance.now())
      }
    },
  }
}

function installMatchMedia(reducedMotion: boolean): void {
  ;(window as unknown as { matchMedia: typeof window.matchMedia }).matchMedia = vi.fn(
    (query: string) =>
      ({
        matches: reducedMotion && query.includes('prefers-reduced-motion'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }) as unknown as MediaQueryList,
  )
}

type Ambiance = ReturnType<typeof useAmbiance>

// useAmbiance registers onUnmounted — give it a real component instance.
function mountAmbiance(): { ambiance: Ambiance; wrapper: { unmount: () => void } } {
  let ambiance!: Ambiance
  const wrapper = mount(
    defineComponent({
      setup() {
        ambiance = useAmbiance()
        return () => null
      },
    }),
  ) as unknown as { unmount: () => void; vm: ComponentPublicInstance }
  return { ambiance, wrapper }
}

function cssVar(name: string): string {
  return document.documentElement.style.getPropertyValue(name)
}

describe('useAmbiance beat pulse', () => {
  let raf: { tick: (n?: number) => void }

  beforeEach(() => {
    setActivePinia(createPinia())
    raf = installRAF()
    installMatchMedia(false)
    audioMock.__setBass(0)
  })

  afterEach(() => {
    document.documentElement.style.removeProperty('--ambiance-intensity')
    document.documentElement.style.removeProperty('--ambiance-pulse')
    vi.restoreAllMocks()
  })

  function setBaseIntensity(value: number): void {
    const store = useAmbianceStore()
    store.setAmbiance({
      palette: ['#FF0000', '#00FF00'],
      behavior: 'pulse_fast',
      intensity: value,
      vibe: 'test',
    })
  }

  it('moderate bass on a high base intensity stays proportional instead of clipping at 1', async () => {
    setBaseIntensity(0.9)
    const { ambiance } = mountAmbiance()
    await Promise.resolve()

    audioMock.__setBass(0.3)
    ambiance.start()
    raf.tick(20) // let the envelope converge on 0.3

    const intensity = parseFloat(cssVar('--ambiance-intensity'))
    // Headroom formula: 0.9 + (1 - 0.9) * 0.3 ≈ 0.93. The old multiplicative
    // formula clipped this to 1, making the pulse invisible for loud genres.
    expect(intensity).toBeGreaterThan(0.92)
    expect(intensity).toBeLessThan(0.95)
  })

  it('never exceeds 1 even at full bass on max base intensity', async () => {
    setBaseIntensity(1.0)
    const { ambiance } = mountAmbiance()
    await Promise.resolve()

    audioMock.__setBass(1)
    ambiance.start()
    raf.tick(30)

    expect(parseFloat(cssVar('--ambiance-intensity'))).toBeLessThanOrEqual(1)
  })

  it('rises fast on a bass hit and decays slowly after it (attack < release)', async () => {
    setBaseIntensity(0.9)
    const { ambiance } = mountAmbiance()
    await Promise.resolve()

    audioMock.__setBass(1)
    ambiance.start()
    raf.tick(2) // 3 loud frames total (start runs one synchronously)
    const afterHit = parseFloat(cssVar('--ambiance-intensity'))
    expect(afterHit).toBeGreaterThan(0.95) // fast attack: most of the headroom already lit

    audioMock.__setBass(0)
    raf.tick(3)
    const shortlyAfter = parseFloat(cssVar('--ambiance-intensity'))
    expect(shortlyAfter).toBeGreaterThan(0.94) // slow release: still glowing

    raf.tick(60)
    expect(parseFloat(cssVar('--ambiance-intensity'))).toBeLessThanOrEqual(0.901) // back to base
  })

  it('exposes the smoothed pulse as --ambiance-pulse for CSS consumers', async () => {
    setBaseIntensity(0.5)
    const { ambiance } = mountAmbiance()
    await Promise.resolve()

    audioMock.__setBass(1)
    ambiance.start()
    raf.tick(5)

    expect(parseFloat(cssVar('--ambiance-pulse'))).toBeGreaterThan(0.5)
  })

  it('stop() restores the static base and zeroes the pulse', async () => {
    setBaseIntensity(0.6)
    const { ambiance } = mountAmbiance()
    await Promise.resolve()

    audioMock.__setBass(1)
    ambiance.start()
    raf.tick(5)
    ambiance.stop()

    expect(cssVar('--ambiance-intensity')).toBe('0.6')
    expect(cssVar('--ambiance-pulse')).toBe('0')
  })

  it('does not run the pulse loop when prefers-reduced-motion is set', async () => {
    installMatchMedia(true)
    setBaseIntensity(0.5)
    const { ambiance } = mountAmbiance()
    await Promise.resolve()

    audioMock.__setBass(1)
    ambiance.start()
    raf.tick(10)

    // The store's own sync wrote the base; the loop must not have modulated it.
    expect(cssVar('--ambiance-intensity')).toBe('0.5')
    expect(cssVar('--ambiance-pulse')).toBe('')
  })

  it('a fresh start() after stop() begins from a clean envelope', async () => {
    setBaseIntensity(0.9)
    const { ambiance } = mountAmbiance()
    await Promise.resolve()

    audioMock.__setBass(1)
    ambiance.start()
    raf.tick(10)
    ambiance.stop()

    audioMock.__setBass(0)
    ambiance.start()
    const intensity = parseFloat(cssVar('--ambiance-intensity'))
    // No stale smoothed bass from the previous run.
    expect(intensity).toBeLessThanOrEqual(0.901)
  })
})

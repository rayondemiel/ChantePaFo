import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import TrackWaveform from '../../src/components/TrackWaveform.vue'
import type { MatchInfo } from '../../src/types'

// The live-spectrum bars read useAudio().frequencyData. Mock the module with
// a controllable ref; the extra __setFrequencyData export is test-only.
vi.mock('../../src/composables/useAudio', async () => {
  const { ref } = await import('vue')
  const frequencyData = ref(new Uint8Array(0))
  return {
    useAudio: () => ({ frequencyData }),
    __setFrequencyData: (d: Uint8Array) => {
      frequencyData.value = d
    },
  }
})

type AudioMockModule = typeof import('../../src/composables/useAudio') & {
  __setFrequencyData: (d: Uint8Array) => void
}
const audioMock = (await import('../../src/composables/useAudio')) as AudioMockModule

function barHeights(wrapper: ReturnType<typeof mountWaveform>): number[] {
  return wrapper.findAll('.waveform-bar').map((b) => parseFloat(b.attributes('height') ?? '0'))
}

function avg(values: number[]): number {
  return values.reduce((s, v) => s + v, 0) / values.length
}

function mountWaveform(props: Partial<InstanceType<typeof TrackWaveform>['$props']> = {}) {
  return mount(TrackWaveform, {
    props: {
      progress: 0,
      frozen: false,
      markers: [],
      totalDurationMs: 25000,
      stressLevel: 'normal' as const,
      ...props,
    },
  })
}

describe('TrackWaveform', () => {
  beforeEach(() => {
    audioMock.__setFrequencyData(new Uint8Array(0))
  })

  describe('live spectrum bars', () => {
    it('reshapes bar heights from frequency data while not frozen', async () => {
      const wrapper = mountWaveform({ frozen: false })
      const staticHeights = barHeights(wrapper)

      const bytes = new Uint8Array(128)
      bytes.fill(255, 0, 32) // energy in the low bins only
      audioMock.__setFrequencyData(bytes)
      await nextTick()

      const liveHeights = barHeights(wrapper)
      expect(liveHeights).not.toEqual(staticHeights)
    })

    it('maps low-frequency energy to the left bars and none to the right', async () => {
      const wrapper = mountWaveform({ frozen: false })
      const bytes = new Uint8Array(128)
      bytes.fill(255, 0, 32)
      audioMock.__setFrequencyData(bytes)
      await nextTick()

      const heights = barHeights(wrapper)
      const left = avg(heights.slice(0, 8))
      const right = avg(heights.slice(32, 40))
      expect(left).toBeGreaterThan(right * 2)
    })

    it('falls back to the static shape when the spectrum is silent', async () => {
      const wrapper = mountWaveform({ frozen: false })
      const staticHeights = barHeights(wrapper)

      audioMock.__setFrequencyData(new Uint8Array(128)) // connected but all-zero (e.g. CORS-tainted)
      await nextTick()

      expect(barHeights(wrapper)).toEqual(staticHeights)
    })

    it('ignores live data when frozen (reveal keeps the static shape)', async () => {
      const wrapper = mountWaveform({ frozen: true })
      const staticHeights = barHeights(wrapper)

      const bytes = new Uint8Array(128)
      bytes.fill(200)
      audioMock.__setFrequencyData(bytes)
      await nextTick()

      expect(barHeights(wrapper)).toEqual(staticHeights)
    })

    it('keeps a visible floor on every bar even at full spectrum silence gaps', async () => {
      const wrapper = mountWaveform({ frozen: false })
      const bytes = new Uint8Array(128)
      bytes.fill(255, 0, 4) // a single hot band, everything else silent
      audioMock.__setFrequencyData(bytes)
      await nextTick()

      for (const h of barHeights(wrapper)) {
        expect(h).toBeGreaterThan(3)
      }
    })
  })

  it('renders 40 bars', () => {
    const wrapper = mountWaveform()
    const bars = wrapper.findAll('.waveform-bar')
    expect(bars).toHaveLength(40)
  })

  it('playhead position reflects progress prop', () => {
    const wrapper = mountWaveform({ progress: 0.6 })
    const playhead = wrapper.find('.playhead')
    expect(playhead.exists()).toBe(true)
    expect(playhead.attributes('style')).toContain('left: 60%')
  })

  it('hides playhead when frozen', () => {
    const wrapper = mountWaveform({ progress: 0.5, frozen: true })
    expect(wrapper.find('.playhead').exists()).toBe(false)
  })

  it('renders markers with correct classes based on match_type', () => {
    const markers: MatchInfo[] = [
      { player_id: 'p1', name: 'Alice', time_ms: 5000, match_type: 'bonus' },
      { player_id: 'p2', name: 'Bob', time_ms: 10000, match_type: 'title' },
      { player_id: 'p3', name: 'Carol', time_ms: 15000, match_type: 'artist' },
    ]
    const wrapper = mountWaveform({ markers, totalDurationMs: 25000 })
    const markerEls = wrapper.findAll('.marker')
    expect(markerEls).toHaveLength(3)
    expect(markerEls[0].classes()).toContain('marker-bonus')
    expect(markerEls[1].classes()).toContain('marker-title')
    expect(markerEls[2].classes()).toContain('marker-artist')
  })

  it('does not render markers layer when markers array is empty', () => {
    const wrapper = mountWaveform({ markers: [] })
    expect(wrapper.find('.markers-layer').exists()).toBe(false)
  })

  it('has role=progressbar with correct aria attributes', () => {
    const wrapper = mountWaveform({ progress: 0.45 })
    const root = wrapper.get('.track-waveform')
    expect(root.attributes('role')).toBe('progressbar')
    expect(root.attributes('aria-valuenow')).toBe('45')
    expect(root.attributes('aria-valuemin')).toBe('0')
    expect(root.attributes('aria-valuemax')).toBe('100')
  })

  it('applies critical class when stressLevel is critical', () => {
    const wrapper = mountWaveform({ stressLevel: 'critical', progress: 0.8 })
    expect(wrapper.get('.track-waveform').classes()).toContain('waveform-critical')
    const filledBars = wrapper.findAll('.bar-critical')
    expect(filledBars.length).toBeGreaterThan(0)
  })

  it('does not apply critical class when stressLevel is normal', () => {
    const wrapper = mountWaveform({ stressLevel: 'normal', progress: 0.5 })
    expect(wrapper.get('.track-waveform').classes()).not.toContain('waveform-critical')
    expect(wrapper.findAll('.bar-critical')).toHaveLength(0)
  })

  it('positions markers according to time_ms / totalDurationMs', () => {
    const markers: MatchInfo[] = [
      { player_id: 'p1', name: 'Alice', time_ms: 12500, match_type: 'title' },
    ]
    const wrapper = mountWaveform({ markers, totalDurationMs: 25000 })
    const marker = wrapper.get('.marker')
    expect(marker.attributes('style')).toContain('left: 50%')
  })
})

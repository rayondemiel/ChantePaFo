import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { useBreakpoint } from '../../src/composables/useBreakpoint'

/**
 * jsdom doesn't implement matchMedia, so we stub a controllable version.
 * Each test mounts a tiny component that consumes the composable so we
 * exercise the onMounted wiring exactly as the real app does.
 */
function stubMatchMedia(matches: boolean) {
  const listeners: Array<(e: { matches: boolean }) => void> = []
  const mql = {
    matches,
    media: '',
    onchange: null,
    addEventListener: (_: string, cb: (e: { matches: boolean }) => void) => {
      listeners.push(cb)
    },
    removeEventListener: (_: string, cb: (e: { matches: boolean }) => void) => {
      const idx = listeners.indexOf(cb)
      if (idx >= 0) listeners.splice(idx, 1)
    },
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => true,
  }
  // @ts-expect-error test stub
  window.matchMedia = vi.fn(() => mql)
  return {
    fire(newMatches: boolean) {
      mql.matches = newMatches
      listeners.forEach((cb) => cb({ matches: newMatches }))
    },
  }
}

const Harness = defineComponent({
  setup() {
    return useBreakpoint()
  },
  render() {
    return h('div', this.isMobile ? 'mobile' : 'desktop')
  },
})

describe('useBreakpoint', () => {
  beforeEach(() => {
    // @ts-expect-error test cleanup
    delete window.matchMedia
  })

  it('defaults to desktop (not mobile) before matchMedia fires', async () => {
    stubMatchMedia(false)
    const wrapper = mount(Harness)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toBe('desktop')
  })

  it('reports mobile when the media query matches on mount', async () => {
    stubMatchMedia(true)
    const wrapper = mount(Harness)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toBe('mobile')
  })

  it('reacts to viewport changes via matchMedia change events', async () => {
    const control = stubMatchMedia(false)
    const wrapper = mount(Harness)
    expect(wrapper.text()).toBe('desktop')
    control.fire(true)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toBe('mobile')
    control.fire(false)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toBe('desktop')
  })

  it('does not crash when matchMedia is unavailable', () => {
    // matchMedia is already deleted by beforeEach — no stub this time
    const wrapper = mount(Harness)
    expect(wrapper.text()).toBe('desktop')
  })
})

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Countdown from '../../src/components/Countdown.vue'

describe('Countdown', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the starting digit on mount', () => {
    const wrapper = mount(Countdown, { props: { from: 3 } })
    expect(wrapper.text()).toContain('3')
  })

  it('counts down one step per interval', async () => {
    const wrapper = mount(Countdown, { props: { from: 3, intervalMs: 1000 } })
    expect(wrapper.text()).toContain('3')
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('2')
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('1')
  })

  it('emits done exactly once when reaching 0', async () => {
    const wrapper = mount(Countdown, { props: { from: 3, intervalMs: 1000 } })
    vi.advanceTimersByTime(5000)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('uses default from=3 and intervalMs=1000', async () => {
    const wrapper = mount(Countdown)
    expect(wrapper.text()).toContain('3')
    vi.advanceTimersByTime(3000)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('accepts a custom from value', async () => {
    const wrapper = mount(Countdown, { props: { from: 5, intervalMs: 10 } })
    expect(wrapper.text()).toContain('5')
    vi.advanceTimersByTime(50)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('applies the text-display class to the digit', () => {
    const wrapper = mount(Countdown, { props: { from: 3 } })
    expect(wrapper.get('.countdown-digit').classes()).toContain('text-display')
  })

  it('applies anim-countdown-pop to the digit', () => {
    const wrapper = mount(Countdown, { props: { from: 3 } })
    expect(wrapper.get('.countdown-digit').classes()).toContain('anim-countdown-pop')
  })

  it('does not emit done after unmount', async () => {
    const wrapper = mount(Countdown, { props: { from: 3, intervalMs: 1000 } })
    wrapper.unmount()
    vi.advanceTimersByTime(10000)
    expect(wrapper.emitted('done')).toBeUndefined()
  })
})

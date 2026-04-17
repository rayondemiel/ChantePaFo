import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CircularCountdown from '../../src/components/CircularCountdown.vue'

describe('CircularCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 0, 1, 0, 0, 0))
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the initial duration as integer seconds', () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 15 } })
    expect(wrapper.find('.value').text()).toBe('15')
  })

  it('has role=timer and aria-label', () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 10 } })
    const root = wrapper.get('.circular-countdown')
    expect(root.attributes('role')).toBe('timer')
    expect(root.attributes('aria-label')).toBe('Temps restant')
  })

  it('decrements the visible value as time advances', async () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 5 } })
    expect(wrapper.find('.value').text()).toBe('5')
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.value').text()).toBe('4')
    vi.advanceTimersByTime(2000)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.value').text()).toBe('2')
  })

  it('emits finished when reaching 0', async () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 2 } })
    vi.advanceTimersByTime(2100)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('finished')).toBeTruthy()
    expect(wrapper.emitted('finished')).toHaveLength(1)
  })

  it('freezes when running becomes false', async () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 10, running: true } })
    vi.advanceTimersByTime(2000)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.value').text()).toBe('8')
    await wrapper.setProps({ running: false })
    vi.advanceTimersByTime(5000)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.value').text()).toBe('8')
  })

  it('does not emit finished after unmount', async () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 1 } })
    wrapper.unmount()
    vi.advanceTimersByTime(5000)
    expect(wrapper.emitted('finished')).toBeUndefined()
  })

  it('does not apply stress styling when remaining > 10', () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 20 } })
    expect(wrapper.find('.countdown-warning').exists()).toBe(false)
    expect(wrapper.find('.countdown-critical').exists()).toBe(false)
  })

  it('applies warning styling when remaining <= 10', async () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 15 } })
    vi.advanceTimersByTime(5100)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.value').text()).toBe('10')
    expect(wrapper.get('.circular-countdown').classes()).toContain('countdown-warning')
    expect(wrapper.get('.circular-countdown').classes()).not.toContain('countdown-critical')
  })

  it('applies critical styling with shake when remaining <= 5', async () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 10 } })
    vi.advanceTimersByTime(5100)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.value').text()).toBe('5')
    expect(wrapper.get('.circular-countdown').classes()).toContain('countdown-critical')
    expect(wrapper.find('.value-critical').exists()).toBe(true)
  })

  it('renders the progress circle with a stroke-dashoffset that reflects elapsed time', async () => {
    const wrapper = mount(CircularCountdown, { props: { duration: 10 } })
    const initial = wrapper.get('.ring-progress').attributes('stroke-dashoffset')
    expect(initial).toBeDefined()
    expect(Number.parseFloat(initial ?? '0')).toBeCloseTo(0, 1)

    vi.advanceTimersByTime(5000)
    await wrapper.vm.$nextTick()
    const mid = wrapper.get('.ring-progress').attributes('stroke-dashoffset')
    const circumference = 2 * Math.PI * 28
    expect(Number.parseFloat(mid ?? '0')).toBeGreaterThan(circumference * 0.4)
    expect(Number.parseFloat(mid ?? '0')).toBeLessThan(circumference * 0.6)
  })
})

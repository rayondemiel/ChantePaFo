import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import VolumeControl from '../../src/components/VolumeControl.vue'
import { useVolume } from '../../src/composables/useVolume'

describe('VolumeControl', () => {
  beforeEach(() => {
    localStorage.clear()
    const v = useVolume()
    v.setMusic(0.8)
    if (v.musicMuted.value) v.toggleMusicMute()
  })

  it('renders a slider and a mute button', () => {
    const wrapper = mount(VolumeControl)
    expect(wrapper.find('input[type="range"]').exists()).toBe(true)
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('exposes accessible labels', () => {
    const wrapper = mount(VolumeControl)
    const root = wrapper.find('.volume-control')
    expect(root.attributes('role')).toBe('group')
    expect(root.attributes('aria-label')).toBeTruthy()
    const slider = wrapper.find('input[type="range"]')
    expect(slider.attributes('aria-label')).toBe('Volume musique')
    const button = wrapper.find('button')
    expect(button.attributes('aria-label')).toBeTruthy()
  })

  it('binds the slider value to the current music level', () => {
    const v = useVolume()
    v.setMusic(0.42)
    const wrapper = mount(VolumeControl)
    const slider = wrapper.find('input[type="range"]').element as HTMLInputElement
    expect(parseFloat(slider.value)).toBeCloseTo(0.42)
  })

  it('updates the music level when the slider input event fires', async () => {
    const wrapper = mount(VolumeControl)
    const slider = wrapper.find('input[type="range"]')
    ;(slider.element as HTMLInputElement).value = '0.25'
    await slider.trigger('input')
    expect(useVolume().music.value).toBeCloseTo(0.25)
  })

  it('toggles musicMuted when the mute button is clicked and reflects aria-pressed', async () => {
    const wrapper = mount(VolumeControl)
    const button = wrapper.find('button')
    expect(button.attributes('aria-pressed')).toBe('false')
    await button.trigger('click')
    expect(useVolume().musicMuted.value).toBe(true)
    expect(button.attributes('aria-pressed')).toBe('true')
    await button.trigger('click')
    expect(useVolume().musicMuted.value).toBe(false)
    expect(button.attributes('aria-pressed')).toBe('false')
  })

  it('exposes a data-state attribute reflecting muted/low/high modes', async () => {
    const v = useVolume()
    const wrapper = mount(VolumeControl)
    const button = wrapper.find('button')
    v.setMusic(0.8)
    await wrapper.vm.$nextTick()
    expect(button.attributes('data-state')).toBe('high')
    v.setMusic(0.1)
    await wrapper.vm.$nextTick()
    expect(button.attributes('data-state')).toBe('low')
    await button.trigger('click')
    expect(button.attributes('data-state')).toBe('muted')
  })

  it('changes the visible aria-label when toggled', async () => {
    const wrapper = mount(VolumeControl)
    const button = wrapper.find('button')
    const initial = button.attributes('aria-label')
    await button.trigger('click')
    const muted = button.attributes('aria-label')
    expect(muted).not.toBe(initial)
  })
})

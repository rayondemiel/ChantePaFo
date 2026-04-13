import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import GenreSelector from '../../src/components/GenreSelector.vue'

describe('GenreSelector', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('starts with "all" selected', () => {
    const wrapper = mount(GenreSelector)
    const activeChips = wrapper.findAll('.chip.active')
    expect(activeChips.length).toBeGreaterThanOrEqual(1)
    expect(wrapper.text()).toContain('Tout')
  })

  it('emits update on genre toggle', async () => {
    const wrapper = mount(GenreSelector)
    const rockChip = wrapper.findAll('.chip').find((c) => c.text() === 'Rock')
    await rockChip?.trigger('click')
    const emitted = wrapper.emitted('update')
    expect(emitted).toBeDefined()
    expect(emitted![emitted!.length - 1][0]).toHaveProperty('rock')
  })

  it('deselecting all defaults back to all', async () => {
    const wrapper = mount(GenreSelector)
    // Click "Tout" to deselect it (only selected item)
    const allChip = wrapper.findAll('.chip').find((c) => c.text() === 'Tout')
    await allChip?.trigger('click')
    // Should still have "all" since it's the fallback
    const emitted = wrapper.emitted('update')
    const lastEvent = emitted![emitted!.length - 1][0] as Record<string, number>
    expect(lastEvent).toHaveProperty('all')
  })
})

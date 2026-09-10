import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RoundPodium from '../../src/components/RoundPodium.vue'
import { getPlayerHue } from '../../src/lib/playerHue'

describe('RoundPodium', () => {
  it('renders 3 cards with correct ranks when 3 winners provided', () => {
    const wrapper = mount(RoundPodium, {
      props: {
        winners: [
          { player_id: 'u1', name: 'Alice', time_ms: 1200 },
          { player_id: 'u2', name: 'Bob', time_ms: 2500 },
          { player_id: 'u3', name: 'Carol', time_ms: 4800 },
        ],
      },
    })
    const slots = wrapper.findAll('.podium-slot')
    expect(slots).toHaveLength(3)
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('Bob')
    expect(wrapper.text()).toContain('Carol')
    expect(wrapper.text()).toContain('🥇')
    expect(wrapper.text()).toContain('🥈')
    expect(wrapper.text()).toContain('🥉')
  })

  it('renders placeholders when fewer than 3 winners', () => {
    const wrapper = mount(RoundPodium, {
      props: {
        winners: [{ player_id: 'u1', name: 'Alice', time_ms: 1200 }],
      },
    })
    const slots = wrapper.findAll('.podium-slot')
    expect(slots).toHaveLength(3)
    const placeholders = wrapper.findAll('.podium-slot.placeholder')
    expect(placeholders).toHaveLength(2)
    expect(wrapper.text()).toContain('Alice')
  })

  it('shows a single empty state instead of three placeholders when nobody won', () => {
    const wrapper = mount(RoundPodium, { props: { winners: [] } })
    expect(wrapper.findAll('.podium-slot')).toHaveLength(0)
    expect(wrapper.find('.podium-empty').text()).toContain('Personne')
  })

  it('formats times correctly (3200ms → "3.2s")', () => {
    const wrapper = mount(RoundPodium, {
      props: {
        winners: [
          { player_id: 'u1', name: 'Alice', time_ms: 3200 },
          { player_id: 'u2', name: 'Bob', time_ms: 12500 },
        ],
      },
    })
    expect(wrapper.text()).toContain('3.2s')
    expect(wrapper.text()).toContain('12.5s')
  })

  it('uses hue-based color per player in inline style', () => {
    const wrapper = mount(RoundPodium, {
      props: {
        winners: [
          { player_id: 'u1', name: 'Alice', time_ms: 1200 },
          { player_id: 'u2', name: 'Bob', time_ms: 2500 },
          { player_id: 'u3', name: 'Carol', time_ms: 4800 },
        ],
      },
    })
    const html = wrapper.html()
    expect(html).toContain(`--hue: ${getPlayerHue('u1')}`)
    expect(html).toContain(`--hue: ${getPlayerHue('u2')}`)
    expect(html).toContain(`--hue: ${getPlayerHue('u3')}`)
  })

  it('is a labelled ol with three list items', () => {
    const wrapper = mount(RoundPodium, {
      props: {
        winners: [{ player_id: 'u1', name: 'Alice', time_ms: 1200 }],
      },
    })
    const podium = wrapper.get('.podium')
    expect(podium.element.tagName).toBe('OL')
    expect(podium.attributes('role')).toBeUndefined()
    expect(podium.attributes('aria-label')).toBe('Top 3 du round')
    const items = wrapper.findAll('li')
    expect(items).toHaveLength(3)
  })

  it('places the winner in the middle order (rank-1 is the 2nd child in DOM)', () => {
    const wrapper = mount(RoundPodium, {
      props: {
        winners: [
          { player_id: 'u1', name: 'Alice', time_ms: 1200 },
          { player_id: 'u2', name: 'Bob', time_ms: 2500 },
          { player_id: 'u3', name: 'Carol', time_ms: 4800 },
        ],
      },
    })
    const slots = wrapper.findAll('.podium-slot')
    expect(slots[0].classes()).toContain('rank-2')
    expect(slots[1].classes()).toContain('rank-1')
    expect(slots[2].classes()).toContain('rank-3')
  })
})

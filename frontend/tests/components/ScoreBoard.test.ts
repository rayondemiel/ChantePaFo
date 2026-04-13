import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreBoard from '../../src/components/ScoreBoard.vue'

describe('ScoreBoard', () => {
  it('renders each player row', () => {
    const wrapper = mount(ScoreBoard, {
      props: {
        scores: { u1: 10, u2: 5 },
        players: { u1: { name: 'Alice' }, u2: { name: 'Bob' } },
      },
    })
    const rows = wrapper.findAll('.score-row')
    expect(rows).toHaveLength(2)
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('Bob')
  })

  it('sorts players by score descending', () => {
    const wrapper = mount(ScoreBoard, {
      props: {
        scores: { u1: 5, u2: 20, u3: 10 },
        players: {
          u1: { name: 'Alice' },
          u2: { name: 'Bob' },
          u3: { name: 'Carol' },
        },
      },
    })
    const rows = wrapper.findAll('.score-row')
    expect(rows[0].text()).toContain('Bob')
    expect(rows[1].text()).toContain('Carol')
    expect(rows[2].text()).toContain('Alice')
  })

  it('shows rank numbers starting at 1', () => {
    const wrapper = mount(ScoreBoard, {
      props: {
        scores: { u1: 10, u2: 5 },
        players: { u1: { name: 'Alice' }, u2: { name: 'Bob' } },
      },
    })
    const ranks = wrapper.findAll('.score-rank').map((r) => r.text())
    expect(ranks[0]).toContain('1')
    expect(ranks[1]).toContain('2')
  })

  it('shows points for each player', () => {
    const wrapper = mount(ScoreBoard, {
      props: {
        scores: { u1: 42 },
        players: { u1: { name: 'Alice' } },
      },
    })
    expect(wrapper.get('.score-pts').text()).toContain('42')
  })

  it('falls back to the id when the player is missing', () => {
    const wrapper = mount(ScoreBoard, {
      props: {
        scores: { ghost: 3 },
        players: {},
      },
    })
    expect(wrapper.get('.score-name').text()).toBe('ghost')
  })

  it('renders nothing when scores is empty', () => {
    const wrapper = mount(ScoreBoard, {
      props: { scores: {}, players: {} },
    })
    expect(wrapper.findAll('.score-row')).toHaveLength(0)
  })

  it('reacts to prop changes', async () => {
    const wrapper = mount(ScoreBoard, {
      props: {
        scores: { u1: 1 },
        players: { u1: { name: 'Alice' } },
      },
    })
    expect(wrapper.get('.score-pts').text()).toContain('1')
    await wrapper.setProps({
      scores: { u1: 99 },
      players: { u1: { name: 'Alice' } },
    })
    expect(wrapper.get('.score-pts').text()).toContain('99')
  })
})

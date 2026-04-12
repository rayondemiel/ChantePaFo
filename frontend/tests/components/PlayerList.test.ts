import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PlayerList from '../../src/components/PlayerList.vue'
import { useAuthStore } from '../../src/stores/auth'

describe('PlayerList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('renders all players', () => {
    const wrapper = mount(PlayerList, {
      props: {
        players: [
          { id: 'u1', name: 'Alice', is_host: true },
          { id: 'u2', name: 'Bob', is_host: false },
        ],
      },
    })
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('Bob')
  })

  it('shows host tag', () => {
    const wrapper = mount(PlayerList, {
      props: {
        players: [{ id: 'u1', name: 'Alice', is_host: true }],
      },
    })
    expect(wrapper.find('.tag-host').exists()).toBe(true)
    expect(wrapper.text()).toContain('HOST')
  })

  it('highlights current user with is-me class', () => {
    const auth = useAuthStore()
    auth.setAuth({ token: 'x', username: 'alice', user_id: 'u1' })
    const wrapper = mount(PlayerList, {
      props: {
        players: [{ id: 'u1', name: 'Alice', is_host: false }],
      },
    })
    expect(wrapper.find('.is-me').exists()).toBe(true)
    expect(wrapper.find('.tag-me').exists()).toBe(true)
  })
})

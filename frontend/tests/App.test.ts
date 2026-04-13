import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import App from '../src/App.vue'

describe('App.vue', () => {
  it('mounts with ambiance decoration layers and the router view', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div>home</div>' } }],
    })
    await router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: { plugins: [router, createPinia()] },
    })

    expect(wrapper.find('#app').exists()).toBe(true)
    expect(wrapper.find('.ambiance-glow-1').exists()).toBe(true)
    expect(wrapper.find('.ambiance-glow-2').exists()).toBe(true)
    expect(wrapper.find('.ambiance-stripe').exists()).toBe(true)
  })
})

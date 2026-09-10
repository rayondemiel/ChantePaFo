import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, enableAutoUnmount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import App from '../src/App.vue'
import { useAmbianceStore } from '../src/stores/ambiance'

const connected = ref(false)
const socketMock = {
  connect: vi.fn(),
  emit: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  disconnect: vi.fn(),
  getSocket: vi.fn(),
  connected,
}
vi.mock('../src/composables/useSocket', () => ({
  useSocket: () => socketMock,
}))

// Unmount every wrapper after each test so a lingering App instance's
// connected-watcher can't fire into the next test's fresh mocks.
enableAutoUnmount(afterEach)

async function mountApp() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div>home</div>' } }],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(App, {
    global: { plugins: [router, pinia] },
  })
  return { wrapper, pinia }
}

describe('App.vue', () => {
  beforeEach(() => {
    connected.value = false
    socketMock.on.mockReset()
    socketMock.off.mockReset()
  })

  it('mounts with ambiance decoration layers and the router view', async () => {
    const { wrapper } = await mountApp()

    expect(wrapper.find('#app').exists()).toBe(true)
    expect(wrapper.find('.ambiance-glow-1').exists()).toBe(true)
    expect(wrapper.find('.ambiance-glow-2').exists()).toBe(true)
    expect(wrapper.find('.ambiance-stripe').exists()).toBe(true)
  })

  it('registers the ambiance_update listener when the socket connects', async () => {
    await mountApp()
    expect(socketMock.on).not.toHaveBeenCalled()

    connected.value = true
    await nextTick()

    const call = socketMock.on.mock.calls.find((c) => c[0] === 'ambiance_update')
    expect(call).toBeDefined()
    expect(call![1]).toBeTypeOf('function')
  })

  it('ambiance_update handler updates the ambiance store', async () => {
    const { pinia } = await mountApp()
    connected.value = true
    await nextTick()

    const call = socketMock.on.mock.calls.find((c) => c[0] === 'ambiance_update')
    const handler = call![1] as (data: unknown) => void
    handler({
      palette: ['#FF2D95', '#00F0FF'],
      behavior: 'pulse_beat',
      intensity: 0.8,
      vibe: 'rock',
    })

    setActivePinia(pinia)
    const store = useAmbianceStore()
    expect(store.config.palette).toEqual(['#FF2D95', '#00F0FF'])
    expect(store.config.behavior).toBe('pulse_beat')
    expect(store.config.intensity).toBe(0.8)
    expect(store.config.vibe).toBe('rock')
  })

  it('unregisters the same ambiance_update handler when the socket disconnects', async () => {
    await mountApp()
    connected.value = true
    await nextTick()

    const onCall = socketMock.on.mock.calls.find((c) => c[0] === 'ambiance_update')
    const handler = onCall![1]
    expect(socketMock.off).not.toHaveBeenCalled()

    connected.value = false
    await nextTick()

    const offCall = socketMock.off.mock.calls.find((c) => c[0] === 'ambiance_update')
    expect(offCall).toBeDefined()
    expect(offCall![1]).toBe(handler)
  })
})

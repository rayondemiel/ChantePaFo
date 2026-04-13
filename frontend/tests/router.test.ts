import { describe, it, expect, beforeEach } from 'vitest'
import router from '../src/router'

describe('router', () => {
  beforeEach(async () => {
    await router.push('/')
    await router.isReady()
  })

  it('has the expected routes wired', () => {
    const names = router.getRoutes().map((r) => r.name)
    expect(names).toContain('home')
    expect(names).toContain('lobby')
    expect(names).toContain('game')
  })

  it('resolves lobby route with props from the code param', () => {
    const route = router.resolve({ name: 'lobby', params: { code: 'FUNK4242' } })
    expect(route.path).toBe('/FUNK4242')
    expect(route.name).toBe('lobby')
  })

  it('resolves game route nested under /:code/play', () => {
    const route = router.resolve({ name: 'game', params: { code: 'ROCK0001' } })
    expect(route.path).toBe('/ROCK0001/play')
  })
})

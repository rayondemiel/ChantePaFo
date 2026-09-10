import { describe, it, expect, vi, afterEach } from 'vitest'
import { randomUnit, randomToken } from '../../src/lib/random'

describe('random (CSPRNG-backed helpers)', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('randomUnit draws from crypto.getRandomValues, never Math.random', () => {
    const mathSpy = vi.spyOn(Math, 'random')
    const cryptoSpy = vi.spyOn(crypto, 'getRandomValues')
    const value = randomUnit()
    expect(mathSpy).not.toHaveBeenCalled()
    expect(cryptoSpy).toHaveBeenCalled()
    expect(value).toBeGreaterThanOrEqual(0)
    expect(value).toBeLessThan(1)
  })

  it('randomUnit spreads over [0, 1)', () => {
    const values = Array.from({ length: 200 }, () => randomUnit())
    expect(Math.min(...values)).toBeLessThan(0.2)
    expect(Math.max(...values)).toBeGreaterThan(0.8)
    expect(new Set(values).size).toBeGreaterThan(190)
  })

  it('randomToken returns lowercase base36 of the requested length', () => {
    const token = randomToken(6)
    expect(token).toMatch(/^[a-z0-9]{6}$/)
    expect(randomToken(12)).toHaveLength(12)
  })

  it('randomToken is unique across draws and uses the crypto source', () => {
    const cryptoSpy = vi.spyOn(crypto, 'getRandomValues')
    const tokens = new Set(Array.from({ length: 100 }, () => randomToken(8)))
    expect(tokens.size).toBe(100)
    expect(cryptoSpy).toHaveBeenCalled()
  })
})

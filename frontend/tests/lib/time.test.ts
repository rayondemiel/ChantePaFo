import { describe, it, expect } from 'vitest'
import { formatTime } from '../../src/lib/time'

describe('formatTime', () => {
  it('formats sub-minute values as "X.Ys"', () => {
    expect(formatTime(3200)).toBe('3.2s')
    expect(formatTime(12500)).toBe('12.5s')
    expect(formatTime(0)).toBe('0.0s')
    expect(formatTime(500)).toBe('0.5s')
  })

  it('rounds to one decimal place', () => {
    expect(formatTime(3249)).toBe('3.2s')
    expect(formatTime(3250)).toBe('3.3s')
  })

  it('formats >= 60000 ms as m:ss', () => {
    expect(formatTime(60000)).toBe('1:00')
    expect(formatTime(65000)).toBe('1:05')
    expect(formatTime(125000)).toBe('2:05')
  })

  it('clamps negatives to 0', () => {
    expect(formatTime(-500)).toBe('0.0s')
  })
})

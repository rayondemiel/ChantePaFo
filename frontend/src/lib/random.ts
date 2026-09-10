/**
 * Randomness helpers backed by the Web Crypto CSPRNG.
 *
 * Nothing in the app needs unpredictable numbers for security (identity
 * and ordering always come from the server), but drawing everything from
 * `crypto.getRandomValues` keeps one source of randomness, avoids the
 * "Math.random is security-sensitive" class of findings, and costs nothing.
 */

const BASE36 = 'abcdefghijklmnopqrstuvwxyz0123456789'

/** Uniform float in [0, 1), like Math.random but from the CSPRNG. */
export function randomUnit(): number {
  const buf = new Uint32Array(1)
  crypto.getRandomValues(buf)
  return buf[0]! / 2 ** 32
}

/** Lowercase base36 token of `length` characters (unbiased draw per char). */
export function randomToken(length: number): string {
  const bytes = new Uint8Array(length)
  crypto.getRandomValues(bytes)
  let out = ''
  for (const b of bytes) {
    // 252 = 7 × 36: rejecting the tail keeps every char equiprobable.
    let v = b
    while (v >= 252) {
      const one = new Uint8Array(1)
      crypto.getRandomValues(one)
      v = one[0]!
    }
    out += BASE36[v % 36]
  }
  return out
}

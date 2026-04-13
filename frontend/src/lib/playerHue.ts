export function getPlayerHue(id: string): number {
  let h = 5381
  for (const ch of id) {
    h = ((h << 5) + h + (ch.codePointAt(0) ?? 0)) >>> 0
  }
  return h % 360
}

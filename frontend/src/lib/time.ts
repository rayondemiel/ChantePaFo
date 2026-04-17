export function formatTime(ms: number): string {
  const safe = Math.max(0, Math.floor(ms))
  if (safe >= 60000) {
    const minutes = Math.floor(safe / 60000)
    const seconds = Math.floor((safe % 60000) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }
  const tenths = Math.round(safe / 100) / 10
  return `${tenths.toFixed(1)}s`
}

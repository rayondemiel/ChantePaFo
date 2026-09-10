import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { AmbianceConfig } from '../types'

export const useAmbianceStore = defineStore('ambiance', () => {
  // Same values as the backend's "lobby" moment (app/ambiance/engine.py) so a
  // client that loads without receiving ambiance_update (reload, deep link)
  // glows like everyone else in the room.
  const config = ref<AmbianceConfig>({
    palette: ['#334466', '#223355', '#445577'],
    behavior: 'breathe_slow',
    intensity: 0.3,
    vibe: 'waiting',
  })

  // Sync ambiance to CSS variables whenever config changes
  watch(
    config,
    (c) => {
      const root = document.documentElement
      if (c.palette[0]) root.style.setProperty('--ambiance-color-1', c.palette[0])
      if (c.palette[1]) root.style.setProperty('--ambiance-color-2', c.palette[1])
      root.style.setProperty('--ambiance-intensity', String(c.intensity))
      if (c.bpm && c.bpm > 0) {
        // One beat period, clamped so CSS animations stay sane even if the
        // backend ships an absurd bpm. Consumers scale it (bar breathe, orb
        // drift) so the whole scene paces itself to the genre.
        const period = Math.min(1.5, Math.max(0.3, 60 / c.bpm))
        root.style.setProperty('--ambiance-pulse-speed', `${period.toFixed(3)}s`)
      }
    },
    { deep: true, immediate: true },
  )

  function setAmbiance(data: AmbianceConfig) {
    config.value = data
  }

  return { config, setAmbiance }
})

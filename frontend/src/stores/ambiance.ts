import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { AmbianceConfig } from '../types'

export const useAmbianceStore = defineStore('ambiance', () => {
  const config = ref<AmbianceConfig>({
    palette: ['#3A3A5C', '#5C5C8A'],
    behavior: 'breathe_slow',
    intensity: 0.2,
    vibe: 'lobby',
  })

  // Sync ambiance to CSS variables whenever config changes
  watch(
    config,
    (c) => {
      const root = document.documentElement
      if (c.palette[0]) root.style.setProperty('--ambiance-color-1', c.palette[0])
      if (c.palette[1]) root.style.setProperty('--ambiance-color-2', c.palette[1])
      root.style.setProperty('--ambiance-intensity', String(c.intensity))
    },
    { deep: true, immediate: true },
  )

  function setAmbiance(data: AmbianceConfig) {
    config.value = data
  }

  return { config, setAmbiance }
})

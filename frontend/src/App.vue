<template>
  <div id="app">
    <div class="ambiance-glow-1"></div>
    <div class="ambiance-glow-2"></div>
    <div class="ambiance-stripe"></div>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { provideBreakpoint } from './composables/useBreakpoint'
import { useSocket } from './composables/useSocket'
import { useAmbianceStore } from './stores/ambiance'
import type { AmbianceConfig } from './types'

// Install the app-wide viewport breakpoint state.
// A single matchMedia listener at the root; all views inject the same ref.
provideBreakpoint()

// Ambiance listener at the app root — survives all route changes. Previously
// lived in GameView, but ambiance_update arrives between game_started and
// GameView mount, racing the navigation: by the time GameView registered its
// listener, the event had already flown by and the store stayed at lobby
// defaults (intensity 0.2). Mounting here removes the race entirely.
const ambianceStore = useAmbianceStore()
const { connected, on, off } = useSocket()

function onAmbianceUpdate(data: unknown) {
  ambianceStore.setAmbiance(data as AmbianceConfig)
}

watch(
  connected,
  (now, prev) => {
    if (now && !prev) on('ambiance_update', onAmbianceUpdate)
    else if (!now && prev) off('ambiance_update', onAmbianceUpdate)
  },
  { immediate: true },
)
</script>

<style>
#app {
  position: relative;
  min-height: 100vh;
  z-index: 1;
}
</style>

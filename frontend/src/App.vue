<template>
  <div id="app">
    <div class="ambiance-glow-1"></div>
    <div class="ambiance-glow-2"></div>
    <div class="ambiance-stripe"></div>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { provideBreakpoint } from './composables/useBreakpoint'

// Install the app-wide viewport breakpoint state.
// A single matchMedia listener at the root; all views inject the same ref.
provideBreakpoint()
</script>

<style>
#app {
  position: relative;
  min-height: 100vh;
  z-index: 1;
}
</style>

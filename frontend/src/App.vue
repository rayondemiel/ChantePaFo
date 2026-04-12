<template>
  <div id="app">
    <div class="ambiance-glow-1"></div>
    <div class="ambiance-glow-2"></div>
    <div class="ambiance-stripe"></div>
    <router-view />
  </div>
</template>

<script setup lang="ts"></script>

<style>
#app {
  position: relative;
  min-height: 100vh;
  z-index: 1;
}
</style>

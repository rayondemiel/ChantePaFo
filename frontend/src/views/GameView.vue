<template>
  <div>Game {{ code }}</div>
</template>

<script setup lang="ts">
defineProps<{ code: string }>()
</script>

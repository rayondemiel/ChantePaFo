<template>
  <div class="finished-actions">
    <template v-if="isHost">
      <button type="button" class="btn btn-secondary" data-test="back-lobby" @click="emit('back')">
        Retour au lobby
      </button>
      <button type="button" class="btn btn-primary" data-test="replay-game" @click="emit('replay')">
        Rejouer
      </button>
    </template>
    <p v-else class="waiting-host" data-test="waiting-host">En attente de l'hôte...</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ isHost: boolean }>()

const emit = defineEmits<{
  back: []
  replay: []
}>()
</script>

<style scoped>
.finished-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--space-sm);
  width: 100%;
  max-width: 400px;
  padding: var(--space-sm) 0;
}

.finished-actions .btn {
  min-height: 48px;
}

.waiting-host {
  text-align: center;
  color: var(--color-text-muted);
  font-family: var(--font-display);
  font-size: var(--text-base);
  letter-spacing: 2px;
  text-transform: uppercase;
  animation: waiting-pulse 2s ease-in-out infinite;
}

@keyframes waiting-pulse {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}

@media (min-width: 768px) {
  .finished-actions {
    flex-direction: row;
    justify-content: center;
    align-items: center;
  }
  .finished-actions .btn {
    min-width: 160px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .waiting-host {
    animation: none;
  }
}
</style>

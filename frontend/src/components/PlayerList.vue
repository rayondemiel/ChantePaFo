<template>
  <div class="player-list">
    <div
      v-for="player in players"
      :key="player.id"
      class="player-card"
      :class="{ me: player.id === currentUserId }"
    >
      <div class="player-avatar">{{ player.name[0]?.toUpperCase() }}</div>
      <span class="player-name">{{ player.name }}</span>
      <span v-if="player.is_host" class="host-badge">👑</span>
      <button
        v-if="canKick && !player.is_host"
        class="btn-kick"
        :aria-label="`Exclure ${player.name}`"
        @click="emit('kick', player.id)"
      >
        ✕
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Player } from '../types'
import { useAuthStore } from '../stores/auth'

withDefaults(
  defineProps<{
    players: Player[]
    canKick?: boolean
  }>(),
  { canKick: false },
)

const emit = defineEmits<{
  kick: [playerId: string]
}>()

const auth = useAuthStore()
const currentUserId = auth.userId
</script>

<style scoped>
.player-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  width: 100%;
}
.player-name {
  flex: 1;
}
.host-badge {
  font-size: 1.2rem;
}
.btn-kick {
  background: none;
  border: 1px solid var(--color-error, #ff4444);
  color: var(--color-error, #ff4444);
  border-radius: var(--radius-sm, 4px);
  padding: 0 var(--space-xs, 4px);
  font-size: var(--text-sm);
  cursor: pointer;
  line-height: 1.4;
  opacity: 0.7;
  transition: opacity 0.15s;
}
.btn-kick:hover {
  opacity: 1;
}
</style>

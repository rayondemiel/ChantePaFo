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
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Player } from '../types'
import { useAuthStore } from '../stores/auth'

defineProps<{ players: Player[] }>()
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
</style>

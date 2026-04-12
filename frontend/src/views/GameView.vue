<template>
  <div class="game-view game-layout">
    <div v-if="!gameStore.state" class="waiting">
      <p>Chargement...</p>
    </div>
    <template v-else>
      <div class="zone-info">
        <span class="text-display">{{ phaseName }}</span>
        <span v-if="gameStore.state.current_round !== undefined" class="round-info">
          Round {{ (gameStore.state.current_round as number) + 1 }} /
          {{ gameStore.state.total_rounds }}
        </span>
      </div>

      <div class="zone-content">
        <p class="phase-label">{{ gameStore.state.phase }}</p>
        <!-- Game mode components will be added in Tasks 21-26 -->
      </div>

      <div v-if="gameStore.awards.length > 0" class="zone-actions">
        <h2 class="text-display">Awards</h2>
        <div v-for="award in gameStore.awards" :key="award.id" class="award-card anim-award-pop">
          <span class="award-emoji">{{ award.emoji }}</span>
          <span class="award-title">{{ award.title }}</span>
          <span class="award-detail">{{ award.detail }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGameStore } from '../stores/game'
import { useAmbianceStore } from '../stores/ambiance'
import { useSocket } from '../composables/useSocket'
import type { GameState, AmbianceConfig, Award } from '../types'

defineProps<{ code: string }>()
const router = useRouter()
const auth = useAuthStore()
const gameStore = useGameStore()
const ambianceStore = useAmbianceStore()
const { connect: socketConnect, on, off } = useSocket()

const phaseName = computed(() => {
  const phase = gameStore.state?.phase
  const map: Record<string, string> = {
    countdown: 'Prêt ?',
    playing: 'À toi de jouer !',
    round_result: 'Résultats',
    finished: 'Terminé !',
    listening: 'Écoute...',
    recording: 'Enregistre !',
    guessing: 'Devine !',
    reveal: 'Révélation',
    singing: 'Chante !',
    writing: 'Écris !',
  }
  return map[phase ?? ''] ?? phase ?? ''
})

function onGameState(data: unknown) {
  gameStore.setState(data as GameState)
}

function onGameEnded(data: unknown) {
  const d = data as { awards: Award[]; total_scores: Record<string, number> }
  gameStore.setFinalResults(d)
}

function onAmbiance(data: unknown) {
  ambianceStore.setAmbiance(data as AmbianceConfig)
}

onMounted(() => {
  // Deep-link guard: a direct navigation to /:code/play without going through
  // the lobby leaves the socket singleton uninitialized. Ensure we're
  // authenticated and connected before subscribing to events.
  if (!auth.token) {
    router.replace('/')
    return
  }
  socketConnect(auth.token)
  on('game_state', onGameState)
  on('game_ended', onGameEnded)
  on('ambiance_update', onAmbiance)
})

onUnmounted(() => {
  off('game_state', onGameState)
  off('game_ended', onGameEnded)
  off('ambiance_update', onAmbiance)
})
</script>

<style scoped>
.game-view {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.waiting {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: var(--color-text-muted);
}
.round-info {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  margin-left: var(--space-sm);
}
.phase-label {
  color: var(--color-accent);
  font-size: var(--text-xl);
  text-align: center;
}
.award-card {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-sm);
}
.award-emoji {
  font-size: 1.5rem;
}
.award-title {
  font-weight: 700;
}
.award-detail {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}
</style>

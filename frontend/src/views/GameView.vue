<template>
  <div
    class="game-view game-layout"
    :class="{ 'game-view--locked': gameStore.state && gameStore.state.phase !== 'finished' }"
  >
    <div v-if="!gameStore.state" class="waiting">
      <p>Chargement...</p>
    </div>
    <template v-else>
      <div v-if="gameStore.state.phase !== 'finished'" class="zone-info">
        <div class="zone-info-main">
          <span class="phase-name text-display">{{ phaseName }}</span>
          <span v-if="gameStore.state.current_round !== undefined" class="round-info">
            Manche {{ (gameStore.state.current_round as number) + 1 }} /
            {{ gameStore.state.total_rounds }}
          </span>
        </div>
        <div class="zone-info-actions">
          <VolumeControl v-if="gameStore.state.phase !== 'countdown'" class="zone-info-volume" />
          <button
            type="button"
            class="btn-quit"
            data-test="quit-game"
            aria-label="Quitter la partie"
            @click="confirmQuitOpen = true"
          >
            <span class="btn-quit-icon" aria-hidden="true">&#x2715;</span>
          </button>
        </div>
      </div>

      <!-- Scanlines overlay -->
      <div class="ambient-scanlines" aria-hidden="true"></div>
      <!-- Floating orbs -->
      <div class="ambient-orb ambient-orb-1" aria-hidden="true"></div>
      <div class="ambient-orb ambient-orb-2" aria-hidden="true"></div>

      <div class="zone-content">
        <BlindtestRound v-if="gameMode === 'blindtest'" />
        <p v-else class="phase-label">{{ gameStore.state.phase }}</p>
      </div>

      <!-- Always mounted: a v-if would unmount the reaction listeners (no
           floats during countdown) and reflow the page on every phase flip. -->
      <div
        class="zone-social"
        :class="{ 'zone-social--hidden': gameStore.state.phase === 'countdown' }"
      >
        <ReactionBar />
        <Soundboard />
      </div>
    </template>

    <ConfirmDialog
      :open="confirmQuitOpen"
      title="Quitter la partie ?"
      message="Tu vas quitter la partie en cours. Les autres joueurs continueront sans toi."
      confirm-text="Quitter"
      variant="danger"
      @confirm="onConfirmQuit"
      @cancel="confirmQuitOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGameStore } from '../stores/game'
import { useRoomStore } from '../stores/room'
import { useSocket } from '../composables/useSocket'
import { useAmbiance } from '../composables/useAmbiance'
import BlindtestRound from '../components/BlindtestRound.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import ReactionBar from '../components/ReactionBar.vue'
import Soundboard from '../components/Soundboard.vue'
import VolumeControl from '../components/VolumeControl.vue'
import type { GameState, Award, RoomState } from '../types'

const props = defineProps<{ code: string }>()
const router = useRouter()
const auth = useAuthStore()
const gameStore = useGameStore()
const roomStore = useRoomStore()
const { connect: socketConnect, emit: socketEmit, on, off } = useSocket()
const { start: startAmbiance, stop: stopAmbiance } = useAmbiance()

const confirmQuitOpen = ref(false)

const gameMode = computed(() => roomStore.room?.settings.game_mode)

const phaseName = computed(() => {
  const phase = gameStore.state?.phase
  const map: Record<string, string> = {
    countdown: 'Prêt ?',
    playing: 'À toi de jouer !',
    playing_reveal: 'Révélation',
    round_pause: 'Manche suivante',
    round_result: 'Résultats',
    finished: 'Résultats',
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

// Roster changes mid-game (a quit, a host handover) must reach the game
// screen too: the finished ceremony decides who gets the replay buttons
// from roomStore.isHost, and it must not stay frozen on the lobby snapshot.
function onRoomUpdated(data: unknown) {
  roomStore.setRoom(data as RoomState)
}

function onGameEnded(data: unknown) {
  const d = data as { awards: Award[]; total_scores: Record<string, number> }
  gameStore.setFinalResults(d)
}

function onLeftGame() {
  gameStore.reset()
  router.push('/')
}

function onReturnedToLobby(data: unknown) {
  const d = data as { code: string }
  gameStore.reset()
  router.push(`/${d.code ?? props.code}`)
}

function onConfirmQuit() {
  confirmQuitOpen.value = false
  socketEmit('leave_game', { code: roomStore.room?.code ?? props.code })
}

onMounted(() => {
  if (!auth.token) {
    router.replace('/')
    return
  }
  socketConnect(auth.token)
  on('game_state', onGameState)
  on('game_ended', onGameEnded)
  on('room_updated', onRoomUpdated)
  // ambiance_update is handled at the App root (App.vue) so it can't race
  // the route transition into /game.
  on('left_game', onLeftGame)
  on('returned_to_lobby', onReturnedToLobby)
  startAmbiance()
})

onUnmounted(() => {
  off('game_state', onGameState)
  off('game_ended', onGameEnded)
  off('room_updated', onRoomUpdated)
  off('left_game', onLeftGame)
  off('returned_to_lobby', onReturnedToLobby)
  stopAmbiance()
})
</script>

<style scoped>
.game-view {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  overflow: hidden;
}
.waiting {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: var(--color-text-muted);
}
.zone-info {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-md);
  background: linear-gradient(
    180deg,
    rgba(var(--color-bg-rgb), 0.97),
    rgba(var(--color-bg-rgb), 0.85)
  );
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border);
}
.zone-info-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  min-width: 0;
}
.zone-info-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}
.zone-info-volume {
  flex-shrink: 0;
}
.btn-quit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(var(--color-error-rgb), 0.3);
  border-radius: var(--radius-full);
  background: rgba(var(--color-error-rgb), 0.08);
  color: var(--color-error);
  font-size: var(--text-sm);
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    transform 0.1s;
}
.btn-quit:hover {
  background: rgba(var(--color-error-rgb), 0.18);
  border-color: rgba(var(--color-error-rgb), 0.5);
  transform: scale(1.05);
}
.btn-quit:active {
  transform: scale(0.95);
}
.btn-quit-icon {
  line-height: 1;
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

/* === Ambient background effects === */
.ambient-scanlines {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(var(--color-white-rgb), 0.015) 2px,
    rgba(var(--color-white-rgb), 0.015) 4px
  );
  mix-blend-mode: overlay;
  opacity: 0.5;
}

.ambient-orb {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.ambient-orb-1 {
  top: 15%;
  left: 10%;
  width: 180px;
  height: 180px;
  background: var(--ambiance-color-1);
  filter: blur(90px);
  opacity: calc(var(--ambiance-intensity) * 0.35);
  /* Drift period scales with the track bpm (40 beats per crossing). */
  animation: ambient-drift-1 calc(var(--ambiance-pulse-speed, 0.5s) * 40) ease-in-out infinite
    alternate;
}

.ambient-orb-2 {
  bottom: 20%;
  right: 10%;
  width: 140px;
  height: 140px;
  background: var(--ambiance-color-2);
  filter: blur(70px);
  opacity: calc(var(--ambiance-intensity) * 0.25);
  animation: ambient-drift-2 calc(var(--ambiance-pulse-speed, 0.5s) * 50) ease-in-out infinite
    alternate;
}

.zone-content {
  position: relative;
  z-index: 1;
  /* Absorb the viewport's free space so the game body fills the screen —
     otherwise the leftover 100vh space pools as a dead gap between the
     content and the social bar. */
  flex: 1;
  display: flex;
  flex-direction: column;
}

.zone-content > * {
  flex: 1;
}

.zone-social {
  /* Sticky bottom: stays under the thumb while scrolling the awards
     ceremony — the peak social moment used to be two screens away. */
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md) calc(var(--space-md) + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(180deg, transparent, rgba(var(--color-bg-rgb), 0.92) 40%);
  transition:
    opacity 0.3s var(--ease-smooth),
    transform 0.3s var(--ease-smooth);
}

.zone-social--hidden {
  opacity: 0;
  transform: translateY(8px);
  pointer-events: none;
}

.phase-name {
  white-space: nowrap;
}

@media (max-width: 899px) {
  .btn-quit {
    width: 48px;
    height: 48px;
  }
  /* Phones: the header is one line — phase + round on the left, a compact
     volume pill and the quit button on the right. */
  .zone-info {
    padding: var(--space-sm) var(--space-md);
  }
  .zone-info-main {
    flex: 1 1 auto;
  }
  .phase-name {
    font-size: var(--text-base);
  }
  .round-info {
    margin-left: 0;
  }
  .zone-info-volume :deep(.volume-slider) {
    width: clamp(56px, 16vw, 110px);
  }
}

@media (min-width: 900px) {
  .zone-social {
    flex-direction: row;
    justify-content: center;
    gap: var(--space-lg);
  }
  /* Desktop convention: interactive phases are locked to the viewport — the
     page never scrolls; the round content scrolls internally if it has to.
     The finished ceremony is the one long, scrollable screen. */
  .game-view--locked {
    height: 100vh;
    min-height: 0;
  }
  .game-view--locked .zone-content {
    min-height: 0;
  }
}

@keyframes ambient-drift-1 {
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(30px, 20px);
  }
}

@keyframes ambient-drift-2 {
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(-25px, -15px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ambient-orb-1,
  .ambient-orb-2 {
    animation: none;
  }
}

/* Blindtest and other game modes need the full viewport — override the
   1200px utility cap applied by global .game-layout. */
@media (min-width: 768px) {
  .game-view.game-layout {
    max-width: none;
    margin: 0;
  }
}
</style>

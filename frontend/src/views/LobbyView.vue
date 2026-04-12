<template>
  <div v-if="roomStore.room" class="lobby">
    <div class="zone-info">
      <button
        type="button"
        class="room-code room-code-btn"
        :aria-label="`Copier le code ${roomStore.room.code}`"
        @click="copyCode"
      >
        {{ roomStore.room.code }}
      </button>
      <p class="share-hint">
        <span>{{ roomStore.room.players.length }}/10 joueurs • Partage ce code à tes potes !</span>
      </p>
      <div class="share-actions">
        <button class="btn btn-ghost btn-sm" @click="copyCode">📋 Copier</button>
        <button v-if="canNativeShare" class="btn btn-ghost btn-sm" @click="nativeShare">
          📤 Partager
        </button>
        <button class="btn btn-ghost btn-sm" @click="leaveRoom">🚪 Quitter</button>
      </div>
      <p v-if="toast" class="toast">{{ toast }}</p>
    </div>

    <div class="zone-content">
      <PlayerList
        :players="roomStore.room.players"
        :can-kick="roomStore.isHost"
        @kick="kickPlayer"
      />

      <template v-if="roomStore.isHost">
        <h3 class="text-display">Mode de jeu</h3>
        <select v-model="gameMode" class="input-text" @change="updateSettings">
          <option value="blindtest">Blindtest</option>
          <option value="karaoke">Karaoké Mystère</option>
          <option value="telephone">Téléphone Arabe</option>
        </select>

        <div v-if="gameMode === 'karaoke'">
          <select v-model="karaokeVariant" class="input-text" @change="updateSettings">
            <option value="classic">Classique</option>
            <option value="progressive">Progressif</option>
          </select>
        </div>

        <h3 class="text-display">Manches</h3>
        <select v-model.number="numRounds" class="input-text" @change="updateSettings">
          <option :value="3">3</option>
          <option :value="5">5</option>
          <option :value="10">10</option>
          <option :value="15">15</option>
        </select>

        <h3 class="text-display">Genres</h3>
        <GenreSelector @update="onGenresUpdate" />
      </template>

      <div v-else class="waiting">
        <p>En attente du lancement par l'hôte...</p>
      </div>
    </div>

    <div v-if="roomStore.isHost" class="zone-actions">
      <button
        class="btn btn-primary full-width"
        :disabled="(roomStore.room?.players.length ?? 0) < 2"
        @click="startGame"
      >
        Lancer la partie
      </button>
    </div>

    <p v-if="errorMsg" class="feedback feedback-wrong">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { useSocket } from '../composables/useSocket'
import PlayerList from '../components/PlayerList.vue'
import GenreSelector from '../components/GenreSelector.vue'
import type { RoomState, GameState } from '../types'

const props = defineProps<{ code: string }>()
const router = useRouter()
const roomStore = useRoomStore()
const gameStore = useGameStore()
const { emit: socketEmit, on, off, disconnect: socketDisconnect } = useSocket()

const auth = useAuthStore()
const gameMode = ref('blindtest')
const numRounds = ref(10)
const karaokeVariant = ref('classic')
const errorMsg = ref('')
const toast = ref('')
const canNativeShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

let toastTimer: ReturnType<typeof setTimeout> | null = null
function showToast(message: string) {
  toast.value = message
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = ''
  }, 2000)
}

async function copyCode() {
  if (!roomStore.room) return
  try {
    await navigator.clipboard.writeText(roomStore.room.code)
    showToast('Code copié !')
  } catch {
    showToast('Impossible de copier')
  }
}

async function nativeShare() {
  if (!roomStore.room || !navigator.share) return
  try {
    await navigator.share({
      title: 'ChantePaFo',
      text: `Rejoins ma partie ChantePaFo avec le code ${roomStore.room.code} !`,
      url: window.location.href,
    })
  } catch {
    // user cancelled share — silent
  }
}

function leaveRoom() {
  if (!roomStore.room) return
  if (!window.confirm('Quitter la room ?')) return
  // Disconnecting triggers the server-side _handle_disconnect which
  // calls svc.leave_room and broadcasts room_updated to the other players.
  socketDisconnect()
  roomStore.clearRoom()
  router.push('/')
}

function updateSettings() {
  socketEmit('update_settings', {
    code: props.code,
    settings: {
      game_mode: gameMode.value,
      num_rounds: numRounds.value,
      karaoke_variant: karaokeVariant.value,
    },
  })
}

function onGenresUpdate(genres: Record<string, number>) {
  socketEmit('update_settings', {
    code: props.code,
    settings: { genres },
  })
}

function startGame() {
  socketEmit('start_game', { code: props.code })
}

function kickPlayer(playerId: string) {
  socketEmit('kick_player', { code: props.code, player_id: playerId })
}

function onRoomUpdated(data: unknown) {
  roomStore.setRoom(data as RoomState)
}

function onGameState(data: unknown) {
  gameStore.setState(data as GameState)
  router.push(`/${props.code}/play`)
}

function onError(data: unknown) {
  const d = data as { message?: string }
  errorMsg.value = d.message ?? 'Erreur inconnue'
}

function onPlayerKicked(data: unknown) {
  const d = data as { player_id?: string }
  if (d.player_id === auth.userId) {
    roomStore.clearRoom()
    window.alert("Tu as été exclu de la room par l'hôte.")
    router.push('/')
  }
}

onMounted(async () => {
  // 1. Register event listeners FIRST so we don't miss any events
  on('room_updated', onRoomUpdated)
  on('game_state', onGameState)
  on('game_started', onGameState)
  on('error', onError)
  on('player_kicked', onPlayerKicked)

  // 2. Ensure we're in the Socket.IO room (fixes race where the host's
  //    initial join_room was sent before the WebSocket was fully connected)
  socketEmit('join_room', { code: props.code })

  // 3. Fetch current room state to catch any updates missed during navigation
  if (auth.token) {
    const resp = await auth.authFetch(`/api/rooms/${props.code}`)
    if (resp.ok) {
      const data = await resp.json()
      roomStore.setRoom(data.room)
    }
  }
})

onUnmounted(() => {
  off('room_updated', onRoomUpdated)
  off('game_state', onGameState)
  off('game_started', onGameState)
  off('error', onError)
  off('player_kicked', onPlayerKicked)
})
</script>

<style scoped>
.lobby {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.room-code-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font: inherit;
  color: inherit;
  display: block;
  margin: 0 auto;
}
.room-code-btn:hover {
  opacity: 0.85;
}
.share-hint {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}
.share-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
  margin-top: var(--space-sm);
}
.btn-ghost {
  background: transparent;
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.15));
  color: var(--color-text);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  font-size: var(--text-sm);
  transition: background 0.15s;
}
.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.08);
}
.btn-sm {
  font-size: var(--text-sm);
}
.toast {
  text-align: center;
  color: var(--color-primary);
  font-size: var(--text-sm);
  margin-top: var(--space-xs);
  animation: fadeIn 0.2s ease-out;
}
h3 {
  font-size: var(--text-lg);
  margin-top: var(--space-md);
}
.waiting {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-xl);
}
.full-width {
  width: 100%;
}
</style>

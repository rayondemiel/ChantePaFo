<template>
  <div v-if="roomStore.room" class="lobby">
    <div class="zone-info">
      <p class="room-code">{{ roomStore.room.code }}</p>
      <p class="share-hint">Partage ce code à tes potes !</p>
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
const { emit: socketEmit, on, off } = useSocket()

const auth = useAuthStore()
const gameMode = ref('blindtest')
const numRounds = ref(10)
const karaokeVariant = ref('classic')
const errorMsg = ref('')

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
    router.push('/')
  }
}

onMounted(async () => {
  // Fetch current room state to catch any updates missed during navigation/connection
  if (auth.token) {
    const resp = await auth.authFetch(`/api/rooms/${props.code}`)
    if (resp.ok) {
      const data = await resp.json()
      roomStore.setRoom(data.room)
    }
  }

  on('room_updated', onRoomUpdated)
  on('game_state', onGameState)
  on('game_started', onGameState)
  on('error', onError)
  on('player_kicked', onPlayerKicked)
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
.share-hint {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
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
